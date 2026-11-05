# Dynamite | Agile — Fondations techniques (branche open source `open/v0.60`)

> Depuis 0.60.01 : outil générique et open source pour les étudiants du baccalauréat en conception de produit,
> installé par chacun sur un VPS Linux. Les sections ci-dessous gardent les règles techniques du noyau ; les décisions
> antérieures citées par leur numéro sont indexées dans `docs/DECISIONS_ANTERIEURES.md`.

## À coller dans le champ Instructions du projet Claude de Dynamite | Agile

---

## 1. Contexte et répartition du travail

Dynamite | Agile est une plateforme web unique (noyau `core/` + modules : Dynamite, Agile, Goldmine, Testing,
Exploration, Tools, Training, Timesheet, Help, About) qu'une équipe étudiante installe sur son propre serveur Linux
et personnalise. Aucune donnée ne transite par un service externe ; la page ne charge aucune ressource externe.

**Un seul projet Claude, sur un seul compte, porte le code** (D-O-018, section 11), un chantier à la fois. Le dépôt
git (`Dynamite_Agile/`) est la seule source de vérité du code, de l'état d'avancement (`docs/ETAT_PROJET.md`) et des
décisions (`docs/DECISIONS.md`).

Le noyau `core/` évolue seulement par **lots versionnés** (v0.2, v0.3…) :
chaque changement au noyau est proposé, justifié et validé par
l'utilisateur avant d'être codé, puis livré séparément du code des
modules. Seul le projet qui détient la session active peut le modifier
(section 11).

## 2. Ce qui est déjà décidé et ne se rediscute pas

**Table 1 : Décisions d'architecture actées**

| Sujet | Décision |
|---|---|
| Comptes utilisateurs | Une seule banque d'utilisateurs pour tous les outils (table `users` du noyau). Une connexion, tous les outils accessibles. |
| Droits d'accès | Par projet, au niveau lecteur/éditeur (table `memberships`), plus un rôle administrateur global. Chaque nouvel outil réutilise ce même modèle — jamais son propre système de comptes ou de rôles. |
| Sessions | Cookie `HttpOnly` + `SameSite=Strict`, jeton CSRF vérifié sur toute requête d'écriture. Sur HTTPS : cookie `__Host-da_session` + `Secure`, session liée au certificat client quand mTLS (D-B-090). |
| Mots de passe | PBKDF2-HMAC-SHA256, 310 000 itérations, changement obligatoire à la première connexion. |
| Journal d'audit | Toute action d'écriture est journalisée (qui, quoi, quand) dans une table `audit_log` commune. |
| Réseau | Serveur Linux (VPS), aucune ressource externe (pas de CDN, pas de police Google, pas d'appel à un service cloud). Le réseau n'est pas une zone de confiance : **HTTPS TLS 1.3 obligatoire en production** (certificat du serveur, HSTS), mTLS en option (lot noyau v0.24, D-B-090, `deploy/TLS.md`). |
| Bibliothèques | Bibliothèque standard Python uniquement (`http.server`, `sqlite3`, `hashlib`, `secrets`, `pathlib`), sauf accord explicite pour une exception. Rien à installer par `pip` ou `conda` : Python 3.10 ou plus récent suffit. Aucune bibliothèque tierce dans le navigateur non plus. |
| Chemins de fichiers | Toujours calculés depuis l'emplacement du script (`Path(__file__).parent`), jamais depuis le dossier courant. |
| Taille des fichiers | Chaque fichier Python ou JavaScript reste sous 500 lignes. Un module trop gros se découpe. |
| Langue | Interface, messages d'erreur et commentaires visibles par l'utilisateur en français, **sauf les termes techniques, toujours en anglais** (champs, statuts, types, workflows, catégories, catalogues ; glossaire `docs/GLOSSARY_EN.md`, D-B-085). Code, noms de variables et commentaires techniques en anglais. |
| Évolution du noyau | Par lots versionnés validés à l'avance (voir section 1). Chaque lot met à jour `APP_VERSION` et ce document. |
| Retour utilisateur | Tout refus ou message d'erreur nomme la valeur fautive **et** le correctif (valeurs acceptées, écran où agir, commande à lancer). Un import liste tous les problèmes d'une ligne en une seule passe, avec le numéro de ligne Excel. Jamais d'échec silencieux ni de valeur ignorée sans le dire (D-A-031). |
| Méthode de travail | Workflow en 5 phases par outil (diagnostic d'environnement une fois, puis par exercice : définition du problème, conception, code, compilation si applicable, tests), une question à la fois, attendre la confirmation avant de coder. |

## 3. Comment un nouvel outil se greffe sur le noyau

Le noyau expose un **registre de modules** (`core/modules.py`) : chaque
outil ajoute une entrée avec sa propre base de données, ses propres routes
et son propre onglet, sans jamais modifier le routeur central ni la
navigation.

```python
# core/modules.py — extrait de la structure actuelle
MODULE_MANIFEST = [
    {"key": "dynamite", "label": "Dynamite", "phase": "3.2", "module": None},
    {"key": "agile", "label": "Agile", "phase": "3.3", "module": None},
    # Futur outil, une fois construit :
    # {"key": "changemgmt", "label": "Changements", "phase": "1", "module": changemgmt},
]
```

**Table 2 : Ce qu'un module doit fournir**

| Élément | Rôle |
|---|---|
| `SCHEMA` (chaîne SQL) | Ses propres tables, toujours liées à `projects(id)` directement ou via leur table parente (D-A-010) — jamais de `DROP` ou `ALTER` sur une table d'un autre module |
| `MIGRATIONS` (optionnel) | Liste `(version, sql)` appliquée une seule fois chacune, pour modifier une table déjà en service |
| `ROUTES` (liste) | Même forme que `session_api.ROUTES` : `(méthode, motif d'URL, fonction, niveau d'accès)` |
| Étiquette de navigation | Ajoutée dans `MODULE_MANIFEST`, apparaît automatiquement dans la barre du haut une fois `"module"` renseigné |
| `static/js/<clé>.js`, `static/css/<clé>.css` (optionnel) | Écran propre à l'outil, déclaré par `scripts` et `styles` dans `MODULE_MANIFEST` et chargé par la coquille ; le script appelle `DA.registerModule(clé, render)` (noyau 0.2). Code Python du module dans `modules/<clé>/`. |

Chaque route reçoit un `RequestContext` déjà authentifié et déjà vérifié
pour le CSRF (voir `core/router.py`). Un module n'a jamais à réimplémenter
la connexion, les sessions ou la vérification des droits : il appelle
`core.permissions.require_project_role(conn, user, project_id, "editor")`
et laisse le noyau lever une erreur 403/404 propre si besoin.

**Deux extensions prévues, à concevoir quand on y arrivera :**
- **Messagerie** : aura aussi des messages directs entre deux personnes,
  hors du cadre d'un projet — deuxième mode d'accès à ajouter à
  `core/permissions.py`.
- **Gestion de fichiers** : pensé comme un service de pièces jointes
  partagé (création initiale déclenchée par un ticket Agile ou une page
  Dynamite, édition ensuite dans le navigateur), pas comme un onglet isolé
  — probablement consommé par les autres modules plutôt que autonome.

## 4. Points d'intégration réservés (ne pas construire avant le bon moment)

Ces besoins sont connus mais **volontairement non implémentés** — chacun
suivra son propre cycle Phase 1 à 5 quand l'utilisateur le demandera.
Ne pas les anticiper dans le code d'un autre outil.

- **Notifications courriel** : un serveur de messagerie local en `.ca`
  desservira les notifications Agile et Dynamite (et plus tard les autres
  outils) via `smtplib` vers un relais SMTP interne. Aucune adresse, aucun
  format de message n'est encore défini.
- **Agent de supervision** : un agent de supervision/configuration
  pourrait se greffer sur la plateforme ou rester séparé — décision non
  prise. C'est en partie pourquoi le noyau cible explicitement une base
  « plateforme Linux » plutôt qu'un simple script Windows.
- **Miroir chiffré des fichiers** : VPS distant ou copie locale
  quotidienne, à trancher avec le module Fichiers.

## 5. Identité visuelle et système de conception

L'objectif est d'encourager l'adoption : des interfaces soignées, pas de
gabarit générique. Le noyau utilise déjà un système de jetons CSS que
chaque nouvel outil doit reprendre pour rester visuellement cohérent.

**Table 3 : Jetons de couleur (`static/css/app.css`)**

> À confirmer : le code v0.1 utilise `--dynamite: #e0602f` et `--agile:
> #0e8a8a` (sarcelle), pas les valeurs ci-dessous. Une seule palette sera
> retenue et alignée dans `app.css` et ce tableau.

| Jeton | Rôle | Clair | Sombre |
|---|---|---|---|
| `--dynamite` | Accent wiki (orange mèche du logo) | `#ee6a10` | `#f5863a` |
| `--agile` | Accent action/liens (bleu boussole du logo) | `#0a6fd6` | `#4a9cf2` |
| `--panel` | Barre du haut (bleu marine) | `#0b1b33` | `#071226` |
| `--bg` / `--surface` | Fond de page / cartes | `#f2f4f6` / `#fff` | `#0d1721` / `#15222f` |
| `--danger` / `--warn` / `--ok` | États | rouge / ambre / vert | idem, tons éclaircis |

Un nouvel outil choisit sa propre couleur d'accent (ni l'orange Dynamite ni
le bleu Agile, pour rester identifiable) mais réutilise `--panel`,
`--surface`, `--line`, `--radius-*`, les classes `.btn`, `.badge`, `.table
.data`, `.modal`, `.toast` déjà définies — jamais de nouveau style de
bouton ou de carte inventé en parallèle.

Typographie : `Segoe UI Variable Text` (police système Windows, aucun
fichier à charger). Aucune police Google, aucune icône via CDN — tout
SVG utilisé est inline ou servi localement depuis `static/img/`.

Les logos de marque (mascotte/pictogramme d'un outil, distincts des icônes
fonctionnelles de l'interface) peuvent être des PNG, à condition d'être
servis localement depuis `static/img/`, sans texte intégré à l'image, et
de poids raisonnable (quelques dizaines de Ko). Les icônes fonctionnelles
(types de ticket, actions, états) restent en SVG pour rester nettes à
toute taille et suivre le thème clair/sombre via `currentColor`.

Chaque écran respecte : focus clavier visible, `prefers-reduced-motion`,
mode sombre via `prefers-color-scheme`, aucun texte dans une image (le
texte reste sélectionnable et traduisible).

**Thème par défaut (ex-« Carnet », 0.44.0, D-B-087, lot noyau v0.22 ; renommé en 0.60.01).** Base Atlassian nette pour les tables,
formulaires et textes ; couche « carnet d'ingénieur » (`static/css/sketch.css`, `<html data-sketch>`) :
papier quadrillé, traits de crayon, surligneurs, cartes qui se soulèvent au survol, titres soulignés au surligneur,
notes-bulles au survol (`data-tip`). Écriture manuscrite seulement avec les polices déjà présentes sous Windows
(Segoe Print, Ink Free), jamais de fichier de police. Icônes fonctionnelles : sprite SVG local `static/img/icons.svg`
(`DA.icon(nom)`, `currentColor`) ; logos des outils : croquis colorés `static/img/marks/<clé>.svg` (plus de PNG,
plus de thème minier) ; illustrations `static/img/sketch/`. Tout est généré par `tools/make_sketch_assets.py`
(tracé reproductible) : on modifie le générateur, jamais le SVG à la main. Chaque outil a son surligneur (`--acc`,
`<html data-module>`) : Goldmine jaune, Exploration violet, Agile bleu, Dynamite orange, Testing vert, Tools cyan,
Training rose, Timesheet sarcelle, Admin rouge. Onglets par ordre d'usage (`DA.NAV`, `static/js/tools/sketch.js`) :
Dashboard, Accueil | Goldmine, Exploration, Agile, Dynamite, Testing | Tools, Training, Timesheet ; à droite :
Recherche, Mes éléments, Audit, Help, compte, Admin. Un nouvel outil ajoute son icône au générateur, son entrée
dans `DA.NAV` et son accent dans `sketch.css`. Page vitrine autonome : `static/apps/vitrine/index.html`
(`tools/build_vitrine.py`).

**Terminal R&D (0.45.0, D-B-088, lot noyau v0.23) — thème au choix.** Labo geek façon terminal de développeur moderne,
sur la base sombre (`data-theme="dark"` + `<html data-term>`, `static/css/terminal.css`) : fond presque noir, couleur
de coloration syntaxique par outil (`--acc`), police mono (Cascadia / Consolas, déjà sous Windows) pour titres, clés,
chiffres et boutons ; texte courant en police d'interface. Icônes et logos nets propres au thème, mêmes noms
(`static/img/icons-term.svg`, `static/img/marks-term/`, générés par `tools/make_sketch_assets.py`) : `DA.icon` et
`DA.mark(clé)` choisissent selon le thème — un module appelle toujours `DA.mark("clé")`, jamais un chemin d'image.
Invite de commande sous la barre du haut et séquence de démarrage à la connexion (`static/js/tools/terminal.js`,
seulement dans ce thème, passable d'un clic). **Palette Ctrl+K** (`static/js/tools/palette.js`, tous les thèmes) :
aller à un onglet, un Space ou une page en tapant ; aucune fonction nouvelle, seulement un chemin plus court.
Les zones de module qui redéclarent des jetons clairs (`agile.css`, `dynamite.css`) sont redéclarées en sombre par
`terminal.css` : un nouveau panneau à fond clair codé en dur doit y recevoir son équivalent sombre.

Un thème inconnu (par exemple dans une vieille sauvegarde) revient au Thème par défaut (`prefs.get`, D-O-003).

## 6. Sécurité — à respecter dans tout nouveau module

- Toute route qui modifie des données vérifie le jeton CSRF (déjà fait par
  le routeur pour les méthodes non-GET) et le rôle minimal requis sur le
  projet concerné.
- Toute entrée utilisateur affichée dans une page passe par une liste
  blanche de balises HTML avant stockage (voir le nettoyeur du noyau une
  fois le module Dynamite construit) — jamais d'insertion directe de HTML
  non filtré.
- Le JavaScript construit le DOM avec `el()`/`textContent` (voir
  `static/js/api.js`), jamais avec `innerHTML` sur une donnée venant du
  serveur.
- Chaque action d'écriture appelle `core.audit.log_action(...)` dans la
  même transaction.
- Aucun secret, jeton ou mot de passe n'apparaît dans les journaux
  (`logging`) ni dans les messages d'erreur renvoyés au navigateur.
- Transport (lot noyau v0.24, D-B-090) : un module ne gère jamais TLS ni
  les cookies lui-même ; le noyau sert tout en HTTPS (TLS 1.3), refuse de
  démarrer en production sans certificat (sauf écoute sur 127.0.0.1) et
  expose l'état de la connexion dans `ctx.transport` (version, suite,
  certificat client). Aucune ressource ni lien en `http://`.

## 7. Environnement de développement

Le serveur et les postes n'ont besoin que de Python 3.10 ou plus récent : aucune
installation via `pip`/`conda`. Confirme l'environnement de ce nouveau
compte avant de coder quoi que ce soit (Phase 0), même si l'environnement
Windows/Spyder/Anaconda est probablement identique à celui déjà validé
côté Dynamite/Agile (Python 3.12 via Spyder 6, PyInstaller disponible).

## 8. Portée des nouveaux outils (à traiter un à la fois, phase par phase)

Chacun des outils suivants est un futur module au sens de la section 3.
Aucune conception détaillée n'est faite ici — chacun démarre sa propre
Phase 1 (définition du problème) quand l'utilisateur est prêt à s'y
consacrer :

1. **Gestion du changement** — cycle de vie d'une demande de changement
   (proposition, impact, approbation, mise en œuvre), probablement liée
   aux tickets Agile et aux pages Dynamite concernées.
2. **AMDEC (DFMEA)** — analyse des défaillances du produit conçu par l'équipe.
3. **Messagerie interne** — canaux liés à un projet et messages directs,
   façon Teams/Messenger, en local uniquement.
4. **Gestion de fichiers** — stockage local, création déclenchée par un
   ticket ou une page, édition navigateur, miroir chiffré à définir.

## 9. Ce qui accompagne ce document

- Le code source du noyau (`Dynamite_Agile/`, version 0.1.0), fonctionnel
  et testé jusqu'à l'étape « comptes, projets, droits, administration,
  journal d'audit ». C'est le code de travail de ce projet : il évolue ici,
  selon les règles de la section 1.
- `CLAUDE.md`, à la racine du dépôt : contexte pour Claude Code sur le VPS.
  Doit rester cohérent avec ce document ; en cas d'écart, ce document prime
  et `CLAUDE.md` est corrigé.
- `docs/ETAT_PROJET.md` et `docs/DECISIONS.md` : état courant et registre
  des décisions (section 11).
- `.claude/skills/dynamite-design/SKILL.md` (0.48.0, D-B-093) : la
  section 5 traduite en règles de design pour tout écran (jetons, thèmes
  par défaut et Terminal, icônes, CSP, vérifications). Versionnée comme le code ;
  ce document prime en cas d'écart. Claude Code la charge seul ; un compte
  claude.ai en garde une copie mise à jour depuis le dépôt.
- Ce document, à conserver dans les instructions du projet pour que toute
  nouvelle conversation garde ces conventions sans avoir à les redemander.

## 10. Lot noyau v0.2 (livré en 0.2.0)

**Table 4 : Contenu du lot noyau v0.2**

| # | Changement | Raison |
|---|---|---|
| 1 | Point d'entrée des écrans de module (`DA.registerModule`, scripts listés par `MODULE_MANIFEST`) | Ajouter un onglet sans toucher `app.js` |
| 2 | Migrations versionnées par module (`MIGRATIONS`, version dans `meta`) | Faire évoluer une table après mise en service |
| 3 | Nettoyage `favicon.svg` (bloc `<metadata>` C2PA) et support `HEAD` | Mineur |

Reportés à un lot ultérieur : route binaire pour pièces jointes (images de
pages, fichiers de tickets), éventuel rôle `lead` par projet.

**Lot noyau v0.4 (livré en 0.7.0, D-B-003) : pièces jointes partagées.**
`core/uploads.py` : table `attachments` (migration du module `core`), envoi
brut par une route marquée `@uploads.binary_body` (le corps arrive dans
`ctx.upload`, plafond `max_upload_mb`), type décidé par les premiers octets
(PNG, JPEG, GIF, WebP ; SVG refusé), stockage dédupliqué dans
`data/attachments/<projet>/`, renvoi par `RawFile.image()` après
vérification du rôle par le module. Côté navigateur : `DA.api.upload(url,
fichier)`. Toujours reporté : rôle `lead`, nettoyage des fichiers orphelins.

**Lot noyau v0.5 (livré en 0.10.0, D-B-012) : préparation d'un nouveau projet.**
Un module peut exposer `on_project_created(ctx, project_id)` ; `core/admin.py`
appelle ces fonctions dans l'ordre de `MODULE_MANIFEST`, dans la même
transaction que la création du projet (un échec annule tout). Résultat : un
projet créé est prêt dans chaque onglet (Dynamite : page d'accueil au nom du
projet ; Agile avec Change Management ; Goldmine). `"provision": false`
(API seulement) crée un projet nu, pour les tests.

**Lot noyau v0.6 (livré en 0.11.0, D-B-016) : règles d'accès en texte et annuaire.**
`core/access_rules.py` : migration `core` v2 (colonnes `users.title`,
`expertise`, `route_when`) ; export / import des utilisateurs, de leur
fonction, expertise, « quand leur adresser une question » et de leurs droits
par projet dans un script texte lisible (`utilisateur`, `fonction`,
`expertise`, `diriger`, `droit` ; `aucun` retire un droit). Import vérifié à
blanc avant d'être appliqué ; il crée ou met à jour, ne supprime jamais un
compte, ne retire jamais le dernier admin ; un compte créé reçoit un mot de
passe temporaire (changement obligatoire). Ni les projets ni les mots de
passe ne sont exportés. Base par défaut : `deploy/utilisateurs_exemple.txt`.
Route `GET /api/directory` (annuaire « Qui contacter ? » de l'accueil).

**Lot noyau v0.7 (livré en 0.13.0, D-B-022) : outils de la barre du haut.**
Recherche par mot-clé : `core/search.py` (`GET /api/search?q=`), limitée aux
projets visibles ; chaque module répond par un crochet `search(conn,
projects, terms, limit)` (Dynamite, Agile / Goldmine, Exploration,
Generator) ; tous les mots, accents et majuscules ignorés ; recherches
récentes gardées dans le navigateur. Audit de l'interface :
`core/ui_audit.py` (migration `core` v3, table `ui_audits`, captures dans
`data/ui_audit/`, statut géré par les admins). Crochet `on_startup(ctx)` par
module, lancé au démarrage (`core/startup.py`) ; `admin.create_project_record`
réutilisable. Côté navigateur : `DA.topbarTools` (outils à gauche du menu
utilisateur) et `DA.coreViews` (écrans `#/search`, `#/audit`), sans toucher
aux modules. Logos de la marge gauche à 75 % (134 px), centrés.

**Lot noyau v0.8 (livré en 0.14.0, D-B-024) : placement d'un onglet.** Une
entrée de `MODULE_MANIFEST` peut porter `"placement": "end"` : son onglet
s'affiche à droite d'« Administration », après une barre verticale (onglet
Help). Par défaut `"main"`.

**Lot noyau v0.9 (livré en 0.15.0, D-B-025) : planification des observations
Audit.** Migration `core` v4 (`ui_audits.target_release`, `assignee_id`),
statut « Planifié » ; routes `GET /api/ui-audit/count`, `POST
/api/ui-audit/bulk`, `GET /api/ui-audit/export.csv` ; bouton « Liste Audit »
(compteur des observations ouvertes) à gauche d'« Audit »
(`static/js/tools/audit_list.js`).

**Lot noyau v0.10 (livré en 0.17.0, D-B-027 à D-B-033) : droits,
paramètres, confidentialité, cycle de vie des projets, tableau de bord.**
Rôle de projet `manager` (« Admin du projet », gère les membres de son
projet ; migration `core` 6 qui reconstruit `memberships`) et grille
Administration → Droits (`core/members.py`). Paramètres personnels et
politique de la plateforme (`core/prefs.py`, migration `core` 5 :
`user_prefs`, `app_settings`) ; `/api/me` renvoie `prefs`, `policy`,
`client_ip`. Thèmes par attributs `data-theme` / `data-font` / `data-size` /
`data-density` sur `<html>` (`static/css/themes.css`) ; langue FR/EN de la
coquille (`static/js/tools/i18n.js`, `DA.t`). Confidentialité côté navigateur
(`static/js/tools/privacy.js`) avec journalisation `POST /api/privacy/event`.
Sauvegarde / suppression / restauration de projet (`core/backup.py`, parcours
des clés étrangères, `data/backups/`) et crochet de module
`on_restore(conn, maps, old_key, new_key)`. Tableau de bord
(`core/dashboard.py`) et crochet de module `dashboard(conn, user, projects)`.
Côté navigateur : `DA.applyPrefs`, `DA.myItems()` / `DA.mineBanner()` pour
le filtre « Mes éléments », écrans `#/dashboard`, `#/settings`,
`#/members`.

**Lot noyau v0.11 (livré en 0.21.0, D-B-042 à D-B-048) : configuration,
objectifs, audit.** `core/platform_config.py` (migration `core` 7,
`config_snapshots` : configuration .md à blocs `da:`, aperçu, application,
versions 92 jours) ; `core/objectives.py` (migration `core` 8 : `objectives`,
`objective_comments`, `objective_years`, accès employé + gestionnaire) ;
`core/members.py` : duplication d'un compte ; `core/dashboard.py` :
`?user=` en lecture seule pour les administrateurs ; français seulement
(`prefs.CHOICES["language"] = ("fr",)`) ; confidentialité : flou persistant
jusqu'au clic.

**Lot noyau v0.12 (livré en 0.22.0, D-B-050, D-B-052 à D-B-054) : export et
Sandbox.** `core/prefs.py` : droit individuel `can_export` (donné par un
administrateur, colonne « Export PDF / Word » de la matrice des droits,
journalisé) et préférence `hide_sandbox` ; `core/dashboard.py` écarte
HEADLAMP quand la personne l'a caché ; `app.js` : `DA.sandboxHidden(vue)`,
les Spaces visibles par vue (HEADLAMP reste dans Dynamite et Help), Help et
l'engrenage dans un groupe `nav.tabs-end` qui ne défile jamais ; recherche à
loupe SVG et engrenage sur disque bleu `#267CB5`. « Projet » devient
« Space » dans l'interface (le code et les routes gardent `project`).

**Lot noyau v0.13 (livré en 0.23.0, D-B-057, D-B-058) : traçabilité et
largeur.** Le routeur refuse toute écriture (hors `/api/me/prefs`,
`/api/privacy/event`, `/api/logout`, changement de mot de passe) d'un compte
sans **clé de traçabilité de 3 lettres** (initiales uniques, `prefs.initials`) :
réponse 428 ; `require_initials` (config, vrai par défaut) ne se désactive que
dans les tests. `static/js/tools/initials.js` : avertissement, Paramètres
ouverts dans un nouvel onglet sur la case, bandeau, relecture au retour.
Contenu central fluide (`.content` jusqu'à 2400 px, marges proportionnelles).

**Lot noyau v0.14 (livré en 0.24.0, D-B-061) : identifiants jamais réutilisés.**
Migration `core` 9 : `retired_project_keys` — la clé d'un Space supprimé n'est
jamais redonnée à un nouveau Space (seul le Space lui-même, restauré sous sa
clé d'origine, la reprend avec son compteur de tickets). Les exigences Goldmine
ne s'effacent jamais (statut « Rejetée » / « Obsolète ») ; les codes automatiques
des tâches Exploration viennent d'un compteur qui ne recule pas. Limite
connue : les numéros internes SQLite (non visibles) peuvent être réattribués
si la dernière ligne d'une table est effacée ; les clés visibles, elles, jamais.

**Lot noyau v0.15 (livré en 0.27.0, D-B-074) : outils hors ligne isolés.** Un outil autonome (un fichier
HTML avec scripts et styles intégrés, ex. la page vitrine) vit dans `static/apps/<nom>/`. Le routeur le sert
avec sa propre CSP : code intégré permis, `connect-src 'none'`, rien d'externe, `sandbox` sans
`allow-same-origin` (origine opaque : pas de cookie de session, pas d'appel à `/api/`), `frame-ancestors
'self'`. La plateforme l'affiche dans un `iframe sandbox`. Types statiques `.json` et `.xlsx` ajoutés.

**Lot noyau v0.16 (livré en 0.28.0, D-B-076) : recherche partout et avancée.** `core/search.py` analyse la
requête (mots, \"phrase\", -exclu, clé) et les options (`spaces`, `types`, `in=title`, `since`, `until`, `open`,
`sort`) dans un objet `Query` ; chaque module répond par `search(conn, projects, q)` avec `q.hit(type, q.score(...),
...)` (14 types listés dans `TYPES`) ; le noyau ajoute l'annuaire et l'Audit. Résultats triés par pertinence,
jamais en HTML. Côté navigateur : suggestions pendant la frappe (`search.js`), page `#/search/<mots>?…`
(`search_page.js`).

**Lot noyau v0.17 (livré en 0.30.0, D-B-081) : Testing.** Type de résultat de recherche `test` ; le module
`testing` (onglet après Goldmine) tient une base d'essais unique pour la plateforme, rattachée au Space `TESTING` ;
Goldmine exige qu'une exigence nomme au moins un essai de cette base (« Test Procedure », D-B-080).

**Lot noyau v0.18 (livré en 0.35.0, D-A-039) : menus User et Admin séparés.** L'onglet « User » ne garde que les pages
personnelles (`#/settings`, `#/objectives`, `#/members`) ; l'onglet **Admin** (`#/admin/…`, administrateurs seulement) est tout à
droite de la barre du haut, après le menu à son nom, avec trois groupes (Comptes, Spaces, Plateforme) et l'écran « Setup des
Spaces » (`#/admin/setup`). Un module range ses écrans de réglage dans `DA.adminNav(items, actif, href)` : groupe « ⚙ Admin » de
sa marge gauche, affiché aux administrateurs seulement (Agile → Paramètres du Space ; Timesheet → Export Excel, Spaces et
organismes). Les droits côté serveur ne changent pas.

**Lot noyau v0.19 (livré en 0.38.0, D-A-046) : @mentions.** `core/mentions.py` (migration `core` 10, table `mentions`) : un module appelle `mentions.notify(conn, auteur, texte, kind, href, titre, project_id, source, previous_text)` après une écriture et renvoie `mentions_notice` dans sa réponse (affiché par `api.js`). Routes `GET /api/mentions`, `/api/mentions/count`, `/api/mentions/people`, `POST /api/mentions/read`. Côté navigateur : `static/js/tools/mentions.js` (pastille de l'onglet Dashboard, suggestion « @ », `DA.messagesPanel()`).

**Lot noyau v0.20 (livré en 0.40.0, D-A-048) : PDF.** `core/uploads.py` : `store_pdf(ctx, project_id, module, max_bytes)` garde un PDF (reconnu par « %PDF- ») dans le magasin de pièces jointes ; relu par `uploads.read`.

**Lot noyau v0.21 (livré en 0.41.0, D-A-049) : Admin → Update.** `core/update.py` : export du code (sans `data/`) avec `UPDATE_PROMPT.md` (Claude Opus 5.5 ou plus récent), vérification puis application d'un zip de code (sauvegarde du code et de la base, redémarrage), retour arrière. **Règles de toute mise à jour** : migrations additives seulement (jamais de DROP ni d'effacement de données saisies) ; un champ ou une fonction nouveaux portent `data-new="<version>-<clé>"` (badge « [new] » par `static/js/tools/newtags.js`) ; `UPDATE_LOG.md` à la racine du zip rendu.

**Lot noyau v0.24 (livré en 0.46.0, D-B-090) : transport sécurisé.** `core/tls.py` (bibliothèque standard `ssl`) :
TLS 1.3 seulement (`tls_min_version: "1.2"` = repli ECDHE + AEAD), sans compression ni renégociation ; mTLS codé mais
désactivé par défaut (`tls_client_ca` → optionnel, `tls_client_required: true` → obligatoire, `tls_client_crl`) ;
session liée à l'empreinte SHA-256 du certificat client (migration `core` 12, colonne `sessions.client_cert`,
`tls_bind_session`) ; production **fail closed** (pas de certificat, pas de démarrage, sauf `host` en boucle locale) ;
HSTS (jamais en `dev_mode`), cookie `__Host-`, en-têtes `Referrer-Policy: no-referrer`, `Cross-Origin-Opener-Policy`,
`Cross-Origin-Resource-Policy`, `Permissions-Policy` ; port HTTP de redirection seulement (`http_redirect_port`) ;
écran **Admin → Sécurité réseau** (`/api/admin/transport`, `static/js/admin_transport.js`) ; certificats de
développement `tools/make_dev_ca.py` ; guide `deploy/TLS.md`. Les couches réseau (VPN, VLAN, firewall, 802.1X,
PKI) restent à l'IT.

**Lot noyau v0.25 (livré en 0.47.0, D-B-091) : partage du serveur de développement.** `core/devshare.py` : en
`dev_mode` seulement, `lancer_dev.py reseau` / `--lan` sert la plateforme à un collègue du réseau local — HTTPS avec la
CA de développement (port 8443), réseaux privés et /24 du poste seulement (ou `lan_allow`), refus des autres avant toute
page (routeur), admin / admin accepté seulement depuis le poste serveur (`devshare.guard_login`), formulaire pré-rempli
seulement sur ce poste (`/api/about` → `prefill`). Jamais une configuration de production (FONDATIONS §6, `deploy/TLS.md`).

**Lot noyau v0.26 (livré en 0.49.0, D-B-094) : Admin → Update en trois volets, revue pas à pas.** **Framework** (le code) :
le prompt exige `UPDATE_CHANGES.json` ; après la vérification technique, chaque changement déclaré (et tout fichier non déclaré) est
une étape à ouvrir puis approuver (`core/update_review.py`) ; un refus clôt la revue et produit un « Retour pour Claude » ; rien ne
s'applique avant la dernière approbation (tout ou rien). **Données** (`core/datapack.py`) : comptes sans mots de passe et Spaces
choisis, import par étapes (comptes, puis chaque Space : sauté ou importé comme **nouveau** Space — un Space en service n'est jamais
écrasé). **Site complet** (`core/sitemove.py`) : code + copie exacte de la base + fichiers de `data/`, pour déménager, importé
seulement dans un site vide ; la configuration et les certificats du serveur ne voyagent pas. Les paquets Données et Site complet sont
**scellés** (`core/seal.py` : HMAC-SHA256, clé PBKDF2 310 000 itérations, phrase de passe de 12 caractères au moins), pas chiffrés :
la confidentialité vient du support chiffré de l'IT. Routes marquées `transfer` : plafond `max_transfer_mb`.

**Lot noyau v0.27 (livré en 0.50.0, D-B-098 à D-B-100) : Spaces et réponses.** Marge gauche des pages d'ouverture : liste
des Spaces avec case « par défaut » (préférence `default_space`, un seul Space pour tous les onglets, ouvert par `location.replace`),
« Réinitialiser le Space par défaut », et « Tous les Spaces » (`#/<module>/spaces`) dans un Space (`static/js/tools/spaces.js`,
`DA.spaces`). « Copier / composer un Space » (`core/spacecopy.py`) : toujours un nouveau Space, chaque onglet pris dans un Space
source ou vide, une transaction. Réponse depuis le Dashboard (`core/mentions.py`, migration `core` 13) : commentaire posté à
l'endroit du message avec « @demandeur », « Traités », « Acknowledge ». Un module qui veut une redirection automatique utilise
`location.replace` (jamais `location.hash =` au rendu : piège du bouton Retour, D-B-096). Testing a désormais une Test Base par
Space (TESTING = catalogue de référence, D-B-097).

**Lot noyau v0.30 (livré en 0.50.5, D-B-111) : évaluation annuelle, évaluation de stage, profil professionnel.**
`core/profile.py` (migration core 14 : `user_profiles`, `profile_entries`) : poste fixé par le gestionnaire (employé ou
stagiaire, titre, niveau d'expérience, date d'embauche ; pour un stagiaire : dates, école, programme, tuteur) et parcours
rempli par l'employé (formation, expériences, certifications, compétences, langues), écran `#/profile`.
`core/reviews.py` (migration core 15 : `review_phases`, `review_items`, `review_ratings`) : trois étapes signées par les
deux (début, mi-année, fin ; stagiaire : Accueil, Mi-stage, Évaluation finale), chaque étape ouverte seulement quand la
précédente est signée, lecture seule une fois signée (le gestionnaire peut rouvrir) ; un commentaire de chacun sur chaque
item à mi-année ; un verdict du gestionnaire sur chaque item en fin d'année, l'appréciation globale des deux ; grille de
compétences 1 à 4 et recommandation pour un stagiaire. L'année ne se clôt (`objectives.api_archive`) qu'une fois la fin
signée par les deux. Items = objectifs de l'année + crochet de module `review_items(conn, user_id, year)` (Training : plan
de formation ; `modules.review_hooks()`). Privé comme les objectifs : l'employé et son gestionnaire, administrateurs exclus ;
journal sans texte. Écrans `static/js/tools/objectives.js`, `objectives_review.js`, `review_parts.js`, `profile.js`.
Correctif : `update_review.declared_changes` garde le point de `.claude/…` (un fichier déclaré n'est plus « non déclaré »).

**Lot noyau v0.28 (livré en 0.50.1, D-B-103 à D-B-105) : « 2 × 3 chances » et Update et sauvegardes.** Points de
restauration des données (`core/restorepoints.py`, `data/restore_points/`) : copie exacte de la base prise avant toute
opération de masse (mise à jour ou retour du code, import de données, configuration appliquée, retour à un point), une fois par
jour à la première requête (routeur ; `restore_daily: false` pour couper) et à la main ; **les 3 plus récents gardés**. Un Space
d'un point revient toujours comme **nouveau** Space (`backup.restore(..., skip_conflicts=True)`) ; le retour de tout le site prend
d'abord un point « avant retour », garde le journal d'audit écrit depuis le point (jamais repris), ferme les sessions et réapplique
les migrations du code en service. Les mises à jour gardent **3 copies du code** (`update.prune_code_backups`). Admin : un seul
onglet « Update et sauvegardes » (`#/admin/update/<volet>` : restore, framework, config, data, site ; `#/admin/config` et
`#/admin/backups` redirigent). Coquille : `DA.moduleLayout(main, { picker })` et `DA.spaces.picker(active, href)` donnent à tout
module la liste déroulante des Spaces de Goldmine et Dynamite. Numérotation des versions par le 3e chiffre depuis 0.50.1 (0.50.1 …
0.50.99, puis 0.51.0 ; D-B-107) ; un lot noyau garde son numéro propre.

**Maquette autonome Timesheet (0.36.0, D-A-043) — exception à la règle « Bibliothèques ».** `tools/build_timesheet_demo.py` produit un seul fichier `.html` (hors ligne) qui exécute le vrai serveur de la plateforme dans le navigateur grâce à Pyodide 0.26.4 (Python compilé en WebAssembly, MPL-2.0) : `tools/demo_timesheet/bridge.py` passe chaque requête à `core.router.AppHandler` (seuls les deux envois de réponse sont remplacés), SQLite en mémoire sauvegardé dans IndexedDB. Pyodide n'est utilisé que par ce fichier de démonstration ; la plateforme reste en bibliothèque standard.

**Onglet « User » (0.29.0, D-B-078).** La coquille (`app.js`) regroupe les vues personnelles du noyau
(`#/settings`, `#/objectives`, `#/members`) et, pour un administrateur, `#/admin` sous un onglet « User » avec
sa sous-navigation ; l'engrenage des Paramètres (D-B-034) est retiré.

**Placement « tools » (0.25.0, D-B-065).** Une entrée de `MODULE_MANIFEST` peut
porter `"placement": "tools"` : le module n'a pas d'onglet dans la barre du
haut, il est ouvert depuis l'onglet **Tools** (module `modules/toolbox/`,
clé `tools`) qui reste surligné. Generator (`codex`) est le premier module
ainsi placé. Le Space wiki `TOOLS` porte les pages des méthodes. Tools a deux
sections : Design (`#/tools/design`) et Generator (`#/tools/generator`).

## 11. Un seul projet, un chantier à la fois (D-O-018)

**Table 5 : Règles de travail**

| Sujet | Règle |
|---|---|
| Source de vérité | Le dépôt git. Une décision qui n'est pas dans `docs/DECISIONS.md` n'existe pas. |
| Chantier actif | Un seul chantier à la fois (champ « Chantier actif » de `ETAT_PROJET.md`) ; en changer en fin de livrable, jamais au milieu. |
| Versions | Branche `open/v0.60` ; 0.60.01, puis +1 sur le dernier chiffre à chaque livraison ; un zip du dépôt par livraison. |
| Commits | Après chaque étape qui marche, message clair en français (la version en tête : `0.60.04: …`). |
| Décisions | Numérotation `D-O-001`, `D-O-002`… ; statuts Proposée → Validée → Remplacée (jamais supprimée). Les D-A / D-B antérieures sont indexées dans `docs/DECISIONS_ANTERIEURES.md`. |
| Ce document | Versionné dans le dépôt ; toute modification est recollée le même jour dans les instructions du projet. |

**Début de chaque conversation** : l'utilisateur dépose le zip du dépôt (ou `ETAT_PROJET.md` et `DECISIONS.md`).
Claude lit d'abord ces deux fichiers, lit le bloc « Relais » et reprend à la prochaine action indiquée.

**Fin de chaque livrable** : `ETAT_PROJET.md` à jour (et son bloc « Relais »), les nouvelles entrées de
`DECISIONS.md`, `UPDATE_LOG.md` et `UPDATE_CHANGES.json`, le commit et le zip.

**Lot noyau v0.31 (livré en 0.50.6, D-B-112) : « Mon équipe » et messages de signature.** `core/team.py` : `team_of()` (les
personnes qui ont choisi le gestionnaire dans Paramètres), `GET /api/team` (une ligne par personne : poste, étapes, signatures,
ce qui est attendu du gestionnaire) et `notify_review()` appelé par `core/reviews.py` à chaque signature ou réouverture : un
message `review` (« Évaluation annuelle ») à l'autre partie dans Dashboard → Messages, sans texte privé. `/api/me` expose
`team` (`size`, `pending`) ; le menu du compte affiche « Mon équipe (n) · k à traiter » seulement si `size` > 0 ; écran
`#/team` (`static/js/tools/team.js`). Aucune migration.

**Lot noyau v0.32 (livré en 0.50.7, D-B-114) : worker isolé.** Un fichier `static/**/<nom>_worker.js` reçoit sa
propre politique (`core/router.py`, `WORKER_HEADERS`) : `script-src 'self' 'wasm-unsafe-eval'; connect-src 'none'` —
WebAssembly permis dans le worker seulement, aucun réseau ; la CSP de la page ne change pas. Types statiques `.wasm`,
`.stp`, `.txt` ; `core/uploads.py` : `store_step(...)` garde un fichier STEP dans le magasin de pièces jointes. La
plateforme n'a aucune bibliothèque tierce (`static/vendor/` n'existe pas).

**Lot noyau v0.33 (livré en 0.50.11, D-B-129) : révisions de référence revX.XX et marquage des exports.**
`core/baselines.py` : « Figer une révision » (administrateurs) copie toute la base (API de sauvegarde SQLite, sessions
retirées, compactée, gzip) dans `data/baselines/revX.XX.sqlite.gz` avec sa fiche `revX.XX.json` (titre, motif, qui,
quand, tailles, SHA-256, comptes par table, pièces jointes référencées, empreinte de la fiche précédente : une chaîne).
Numéro revX.XX comparé comme un nombre à deux décimales (rev1.1 = rev1.10) ; automatique = entier suivant ; toujours
strictement plus grand que tout numéro déjà émis (`counter.json`) ; le registre est fait de fichiers, il survit donc à un
retour du site à un point de restauration. `core/baseline_view.py` + `core/router.py` : une personne qui « consulte » une
révision (préférence `baseline_view`) lit, pour toute requête GET, une copie de travail de la révision
(`data/baselines_work/`, schéma du code en service appliqué, comptes / membres / préférences de la base vivante recopiés
avant chaque requête : droits d'aujourd'hui) ; toute écriture est refusée (409 LECTURE_SEULE) sauf les routes de
session et de sortie. `core/stamp.py`, `core/stamp_office.py` : tout fichier construit par la plateforme (Word, Excel,
PowerPoint, CSV, PDF ; `RawFile(..., export=False)` pour un fichier déposé renvoyé tel quel) reçoit la révision dans son
nom (`…_rev1.10.docx`, sinon `…_hors-rev-AAAAMMJJ-HHMM`), dans son en-tête (Word) ou une feuille « Révision » (Excel) et
dans ses propriétés de document ; une ligne chaînée par empreinte est ajoutée au registre `data/baselines/extracts.jsonl`
(qui, initiales, quand, révision, fichier, taille, SHA-256) et au journal d'audit (`data_extracted`). Les révisions
voyagent avec « Site complet » (`sitemove.FILE_DIRS`).

**Lot noyau v0.34 (livré en 0.50.14, D-B-132 à D-B-134) : fiche d'un Space, Spaces prêts partout, module sans écran.**
`core/modules.py` : une entrée de `MODULE_MANIFEST` avec `"placement": "none"` n'a pas d'onglet (`nav_manifest` la saute)
mais garde ses routes et ses crochets ; `space_hooks()` rassemble les crochets `ensure_space(ctx, project_id)` des modules.
`core/startup.py` : `spaces_ready()` appelle chaque crochet pour chaque Space non archivé, à chaque démarrage ; un
crochet est idempotent (ajoute ce qui manque, ne touche jamais au contenu). `core/spacecard.py` : `GET
/api/admin/projects/<id>/card` (contenu par onglet, nombre de comptes qui l'ont par défaut, clé suivante libre) et `POST
…/copy` (dupliquer ou « Enregistrer sous » par `spacecopy.compose`, journalisé `space_saved_as`) ; renommer = nom et
description seulement, la clé ne change jamais. Écran `static/js/admin_spacecard.js` ; `DA.spaces.startHere(titre, texte,
actions)` (`static/js/tools/spaces.js`) pour l'état vide guidé « Commencer ici » d'un onglet. Aucune migration.

## 12. Versions officielles (0.60.12, D-O-024)

- Chaque version publiée a sa fiche `docs/releases/<version>.json` (date, résumé FR / EN, changements et fichiers, comme
  `UPDATE_CHANGES.json`). **À écrire avant de publier une version** : `tools/build_release.py` refuse sans elle, et
  `tests/test_release.py` le vérifie.
- Le paquet officiel est construit par le workflow Pages (`tools/build_release.py --out site/updates`), jamais suivi par git :
  le code seulement, `docs/RELEASE.json` (SHA-256 de chaque fichier), `UPDATE_CHANGES.json` de toute la série (pour les
  portails plus anciens que 0.60.12). Zip reproductible.
- Le serveur ne va jamais sur Internet : Admin → Update renvoie vers `versions.html#depuis=<version>` ; l'administrateur dépose
  le paquet. `core/release.py` : contrôle du manifeste, une étape de revue par version apportée (on peut en sauter
  plusieurs), fichiers modifiés à la main listés, « Plus tard ». `data/` n'est jamais touché ; le code d'avant est gardé.
- Les scripts d'installation (`install.sh`, `install.ps1`) ne bloquent jamais sur du code modifié : une copie
  `data/updates/code-local-*.patch`, puis la branche publiée.


## 13. Agents IA en lecture seule (0.60.35, D-O-044)

- Une route d'accès `"bot"` (`core/bot.py`) ne se lit qu'avec une clé d'agent (`Authorization: Bearer da_bot_…`), faite par un
  administrateur pour des Spaces choisis (⚙ Admin → Bob), gardée en SHA-256, révocable ; jamais de session, de cookie ni
  d'écriture (GET seulement), 60 appels par minute, chaque appel au journal d'audit (`bot_read`).
- La plateforme n'appelle jamais l'agent : c'est lui qui appelle (la règle « aucun appel sortant » tient). Un module peut
  offrir à l'agent sa synthèse par un crochet `bot_summary(conn, pid, key, link)` et ses résultats de recherche par `search`.
- Les réponses portent des liens pointeurs (`/?focus=…&note=…#/…`, `static/js/tools/pointer.js`, D-O-043).

## 14. Mise à jour en ligne (0.60.36, D-O-045)

- Seule exception à la règle « aucun appel sortant », **coupée par défaut** : un administrateur l'active (journalisé) pour un
  serveur qui a accès à Internet. Le serveur ne va alors que sur le site du projet (`release.SITE`, ou `release_site` de la
  config) et seulement quand un administrateur clique « Vérifier maintenant » ou approuve une installation.
- `core/update_online.py` : `versions.json` du site, chaque version plus récente cochée « Lu » (D-B-094), téléchargement,
  SHA-256 publiée, contrôles du paquet officiel (`core/update.check`), sauvegarde du code et point de restauration, puis
  redémarrage. L'écran suit `/progress` (%, étape, lignes) puis `/api/about` jusqu'à la nouvelle version.
- Un module n'appelle jamais le réseau lui-même ; il n'y a pas de vérification automatique en arrière-plan.
