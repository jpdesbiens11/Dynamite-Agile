# Agile (M2) — Architecture V1

**Statut :** Proposée (projet A, 2026-09-23) — à valider avant tout code
**Dépend de :** lot noyau v0.2 (écrans de module, migrations versionnées)
**Hors V1 :** import Jira (aucune donnée à reprendre), pièces jointes
(route binaire du noyau, lot ultérieur), notifications courriel (réservé),
éditeur riche (viendra de Dynamite), champs personnalisés.

---

## 1. Hypothèses d'intake (questions 5 à 8 tranchées par défaut)

**Table 1-1 : Hypothèses retenues — à contredire au besoin**

| # | Sujet | Hypothèse V1 | Évolution prévue |
|---|---|---|---|
| H1 | Configuration des workflows, types et labels | Admin global seulement (Q-02 : pas de rôle `lead` en V1) | Rôle `lead` par projet dans un lot noyau |
| H2 | Qui fait quoi sur les tickets | Lecteur : consulte. Éditeur : crée, modifie, transitionne, commente. Admin : supprime et configure | Restriction par transition (`min_role`) déjà prévue |
| H3 | Types de tickets | Epic, Story, Tâche, Bogue, Sous-tâche créés par défaut ; renommables, ajout possible | — |
| H4 | Workflows | Plusieurs workflows par projet ; chaque type pointe vers un workflow. Défaut : À faire → En cours → En revue → Terminé | Conditions de transition plus riches |
| H5 | Labels | Propres à chaque projet, créés à la volée depuis la fiche ticket (autocomplétion) | Labels globaux si besoin transverse |
| H6 | Priorités | Liste fixe : Bloquante, Haute, Moyenne, Basse, Minime | — |
| H7 | Description et commentaires | Texte simple, retours à la ligne et liens détectés, aucun HTML stocké | Éditeur Dynamite (arbre JSON) |
| H8 | Planification | Sprints (futur, actif, clos ; un seul actif par projet) et versions cibles | Feuille de route M3 |
| H9 | Activation par projet | Bouton admin « Activer Agile » qui crée types et workflow par défaut | — |

## 2. Modèle de données

Préfixe `agile_` sur toutes les tables. Les tables de premier niveau
portent `project_id REFERENCES projects(id) ON DELETE CASCADE` ; les
tables enfants héritent du projet par leur parent (même cascade).

> Précision de règle à valider (FONDATIONS §3, Table 2) : « chaque table
> référence `projects(id)` directement **ou via son parent** ». Répéter
> `project_id` dans chaque table enfant ajouterait des incohérences
> possibles sans gain de sécurité, puisque tout accès passe par le ticket
> ou le workflow, dont le projet est vérifié.

**Table 2-1 : Tables du module Agile**

| Table | Colonnes | Notes |
|---|---|---|
| `agile_settings` | project_id (PK), enabled_at, enabled_by | Présence = Agile activé sur le projet (H9) |
| `agile_workflows` | id, project_id, name, is_default | Un seul `is_default = 1` par projet |
| `agile_statuses` | id, workflow_id, name, category, position, is_initial | `category` ∈ todo, in_progress, done : pilote les couleurs et « résolu » |
| `agile_transitions` | id, workflow_id, from_status_id, to_status_id, name, min_role | `from_status_id` NULL = depuis n'importe quel statut ; `min_role` ∈ editor, admin |
| `agile_issue_types` | id, project_id, name, icon_key, workflow_id, is_subtask, position | `icon_key` = pictogramme SVG local, pas d'image téléversée |
| `agile_issues` | id, project_id, number, type_id, status_id, parent_id, title, description, priority, assignee_id, reporter_id, story_points, due_date, sprint_id, version_id, rank, created_at, updated_at, resolved_at | `UNIQUE(project_id, number)` → clé `PROJ-42` ; `parent_id` = epic ou tâche parente ; `rank` REAL pour l'ordre du backlog |
| `agile_labels` | id, project_id, name, color_key | `UNIQUE(project_id, name COLLATE NOCASE)` |
| `agile_issue_labels` | issue_id, label_id | Clé primaire composée |
| `agile_sprints` | id, project_id, name, goal, state, start_date, end_date | `state` ∈ future, active, closed |
| `agile_versions` | id, project_id, name, release_date, is_released | Version cible (« Fix version ») |
| `agile_comments` | id, issue_id, author_id, body, created_at, edited_at | Texte simple (H7) |
| `agile_links` | id, source_id, target_id, link_type, created_by, created_at | `link_type` ∈ blocks, relates, duplicates ; `UNIQUE(source_id, target_id, link_type)` |
| `agile_history` | id, issue_id, user_id, ts, field, old_value, new_value | Historique de la fiche, distinct de `audit_log` (qui reste le journal de sécurité) |
| `agile_issues_fts` | title, description | Table virtuelle FTS5 synchronisée par déclencheurs ; recherche plein texte |

Numérotation : `number` est pris sur `projects.next_ticket_number` et
incrémenté dans la même transaction (`UPDATE … RETURNING`), donc deux
créations simultanées ne peuvent pas obtenir la même clé.

## 3. Routes API

Toutes les routes sont déclarées avec l'accès `"user"` ; chaque handler
appelle `require_project_role(conn, user, pid, …)` avec le rôle indiqué.
Préfixe commun : `/api/agile/p/<pid>`.

**Table 3-1 : Carte des routes**

| Méthode | Motif | Rôle minimal | Rôle |
|---|---|---|---|
| POST | `/init` | admin | Activer Agile sur le projet (H9) |
| GET | `/meta` | reader | Types, statuts, transitions, labels, sprints, versions, membres : tout ce qu'il faut pour construire les formulaires |
| GET | `/issues` | reader | Liste filtrée : `type`, `status`, `assignee`, `label`, `sprint`, `version`, `q` (FTS), tri, pagination |
| POST | `/issues` | editor | Créer un ticket |
| GET | `/issues/<n>` | reader | Fiche complète : champs, labels, liens, sous-tâches, commentaires, historique |
| PATCH | `/issues/<n>` | editor | Modifier des champs (sauf statut) ; chaque champ modifié → `agile_history` |
| DELETE | `/issues/<n>` | admin | Supprimer (H2) |
| POST | `/issues/<n>/transition` | editor ou `min_role` | Changer de statut uniquement par une transition autorisée |
| PUT | `/issues/<n>/labels` | editor | Remplacer la liste de labels ; crée les labels inconnus (H5) |
| POST / PATCH / DELETE | `/issues/<n>/comments[/<cid>]` | editor ; auteur ou admin pour modifier ou supprimer | Commentaires |
| POST / DELETE | `/issues/<n>/links[/<lid>]` | editor | Liens entre tickets du même projet |
| GET | `/board` | reader | Sprint actif groupé par statut |
| GET | `/backlog` | reader | Sprints futurs et backlog, ordonnés par `rank` |
| PATCH | `/backlog/rank` | editor | Déplacer un ticket (glisser-déposer) |
| POST / PATCH | `/sprints[/<sid>]`, `/sprints/<sid>/start`, `/sprints/<sid>/close` | editor | Cycle des sprints ; la clôture renvoie les tickets non terminés au backlog |
| POST / PATCH / DELETE | `/versions[/<vid>]` | editor | Versions cibles |
| POST / PATCH / DELETE | `/labels[/<lid>]` | admin | Gestion des labels (renommer, couleur, fusion ultérieure) |
| GET / POST / PATCH / DELETE | `/workflows…`, `/statuses…`, `/transitions…`, `/types…` | admin | Configuration ; un statut utilisé par des tickets ne peut pas être supprimé |

## 4. Écrans

Structure reprise de Jira (D-A-006), habillage Dynamite | Agile. Barre du haut du
noyau inchangée ; un panneau latéral propre au module.

**Figure 4-1 : Coquille Agile**

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Dynamite | Agile   Accueil  Dynamite  [Agile]  Administration   JD ▾ │
├───────────────┬──────────────────────────────────────────────────────┤
│ [EQP ▾]       │  EQP / Tableau / Sprint 4                [+ Créer]   │
│               │  Filtres : Assigné ▾  Type ▾  Label ▾  🔍 texte      │
│ ▸ Backlog     │ ┌──────────┬──────────┬──────────┬──────────┐        │
│ ▸ Tableau     │ │ À FAIRE 3│ EN COURS2│ REVUE  1 │ TERMINÉ 4│        │
│ ▸ Tickets     │ │┌────────┐│┌────────┐│          │          │        │
│ ▸ Versions    │ ││EQP-12  │││EQP-9   ││          │          │        │
│ ─────────     │ ││Bogue ● │││Story   ││          │          │        │
│ ⚙ Paramètres  │ ││buse JD │││3 pts JD││          │          │        │
│   (admin)     │ │└────────┘│└────────┘│          │          │        │
└───────────────┴─┴──────────┴──────────┴──────────┴──────────┴────────┘
```

**Figure 4-2 : Fiche ticket (deux panneaux)**

```text
┌─────────────────────────────────────────────┬────────────────────────┐
│ EQP / EQP-12                                │ [En cours ▾] transitions│
│ Surchauffe capteur T3 en charge rapide      │ Assigné      J. Desbiens│
│                                             │ Rapporteur   M. Roy     │
│ Description                                 │ Priorité     Haute      │
│  texte simple…                              │ Type         Bogue      │
│                                             │ Labels       buse, therm │
│ Sous-tâches          [+]                    │ Sprint       Sprint 4   │
│ Liens : bloque EQP-9                        │ Version      v0.3       │
│ ─────────────────────────────────────────── │ Points       3          │
│ [Commentaires] [Historique]                 │ Échéance     2026-10-02 │
│  JD · il y a 2 h : …                        │ Créé / modifié …        │
└─────────────────────────────────────────────┴────────────────────────┘
```

**Figure 4-3 : Formulaire de création (champs de base)**

```text
Type *        [Tâche ▾]          Parent   [aucun ▾]  (epic ou tâche)
Titre *       [____________________________________________]
Description   [                                              ]
Priorité      [Moyenne ▾]        Assigné  [non assigné ▾]
Labels        [buse ×] [therm ×] [+ saisir…]
Sprint        [Backlog ▾]        Version  [aucune ▾]
Points        [__]               Échéance [aaaa-mm-jj]
                                   [Annuler]  [Créer]
```

## 5. Fichiers et découpage

**Table 5-1 : Arborescence (chaque fichier < 500 lignes)**

| Fichier | Contenu |
|---|---|
| `modules/agile/__init__.py` | `SCHEMA`, `MIGRATIONS`, `ROUTES` assemblés |
| `modules/agile/schema.py` | SQL des tables, index, FTS5 et déclencheurs |
| `modules/agile/setup.py` | Activation, types et workflow par défaut |
| `modules/agile/issues.py` | Tickets, labels, liens, commentaires, historique |
| `modules/agile/workflow.py` | Transitions et configuration des workflows et types |
| `modules/agile/planning.py` | Sprints, backlog, rang, versions, tableau |
| `static/js/agile/agile.js` | Coquille, panneau latéral, routage `#/agile/...` |
| `static/js/agile/board.js`, `backlog.js`, `issue.js`, `settings.js` | Un écran par fichier |
| `static/css/agile.css` | Styles propres, basés sur les jetons existants |
| `tests/test_agile_*.py` | Tests bout en bout (`unittest` + `urllib`, bibliothèque standard) |

## 6. Plan incrémental

**Table 6-1 : Incréments (chacun : code → test → validation → suivant)**

| # | Incrément | Test de sortie |
|---|---|---|
| 0 | Lot noyau v0.2 | Un module factice s'affiche dans un onglet ; une migration s'applique une seule fois |
| 1 | Schéma + activation | Activer Agile crée 5 types, 1 workflow, 4 statuts ; refus pour un non-admin |
| 2 | Tickets : créer, lire, modifier, lister | Clés `EQP-1`, `EQP-2` sans doublon en création parallèle ; historique rempli ; lecteur refusé en écriture |
| 3 | Transitions | Transition non autorisée refusée ; `resolved_at` renseigné en catégorie « done » |
| 4 | Labels | Création à la volée, insensible à la casse, filtre par label |
| 5 | Commentaires et liens | Seul l'auteur ou l'admin modifie ; lien vers un autre projet refusé |
| 6 | Sprints, backlog, tableau | Un seul sprint actif ; clôture qui renvoie les tickets ouverts au backlog |
| 7 | Versions et recherche FTS5 | Recherche par mot du titre ou de la description |
| 8 | Écran Paramètres (workflows, types) | Suppression d'un statut utilisé refusée |

Chaque incrément livre aussi sa liste de contrôle de sécurité : rôle
vérifié sur chaque route, CSRF, validation des entrées, audit dans la même
transaction, aucun `innerHTML`.

## 7. v0.3.0 — Import/export CSV, exigences, commentaires filetés

Ajouté après la livraison du MVP, sur demande explicite (2026-09-23).
Décisions : D-A-015 à D-A-020.

**Table 7-1 : Nouveautés**

| Sujet | Choix |
|---|---|
| CSV tickets | `key` vide = création, remplie = mise à jour. Verrou optimiste sur `updated_at` : une ligne changée côté serveur depuis l'export est refusée avec motif, jamais écrasée. Colonne `implements` (clés séparées par `;`). |
| CSV questions/réponses | Seulement les commentaires marqués question et leurs réponses — pas tout le fil interne. `comment_id` rempli = ligne déjà connue, ignorée à l'import (les CSV n'éditent jamais un commentaire existant, seulement en ajoutent). |
| Exigences | Type de ticket avec `is_requirement = 1` (case à cocher dans Paramètres). Lien `implements` : la cible doit être de ce type, sinon 400. Clé complète (`REQ-12`) pour cibler un autre projet ; droit lecteur minimum sur le projet cible. |
| Commentaires | `parent_comment_id` (réponse à), `is_question`, `requirement_ref` (texte libre, non validé), `external_author` (réponse importée sans compte sur la plateforme). |
| Dépendances au backlog | Option A retenue : avertissement visuel seulement sur `blocks`, jamais de blocage de l'action. Endpoint dédié `GET .../dependencies`. |

**Table 7-2 : Format des CSV**

```
tickets.csv:
key,parent_key,type,title,description,priority,status,assignee,labels,sprint,version,points,due_date,updated_at,implements

questions.csv:
issue_key,comment_id,parent_comment_id,requirement_ref,author,is_question,body,created_at
```

## 8. v0.5.0 — Goldmine (exigences d'ingénierie)

Décisions : D-A-032, D-A-033. Code : `modules/agile/goldmine.py`,
`static/js/agile/goldmine.js`, table `agile_requirements` (migration 3).

**Table 8-1 : Routes Goldmine**

| Méthode | Motif | Rôle | Rôle minimal |
|---|---|---|---|
| POST | `/goldmine/setup` | Crée le type Exigence et son workflow | admin |
| GET | `/goldmine` | Exigences + champs + « implémentée par » + manques de traçabilité | reader |
| POST | `/goldmine/requirements` | Crée ticket + fiche en un appel | editor |
| PUT | `/issues/<n>/requirement` | Modifie la fiche (historique par champ) | editor |

**Table 8-2 : Manques de traçabilité signalés**

| Manque | Règle |
|---|---|
| Sans implémentation | Statut Acceptée ou suivant, aucun lien `implements` entrant |
| Sans critère d'acceptation | Statut Acceptée ou suivant |
| Sans réf. de vérification | En vérification ou Vérifiée |
| Sans méthode IADT | Toute exigence non terminée |

Reporté : import/export CSV des champs d'exigence, matrice de vérification,
lignes de base signées, module « test X ».
