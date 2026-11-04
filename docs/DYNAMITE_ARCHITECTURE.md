# Dynamite (M4) — Architecture V1

**Statut :** Proposée (projet A, 2026-09-24) — à valider avant tout code
**Objectif :** les fonctions Confluence réellement utilisées au quotidien,
pas une copie intégrale (voir §1).

---

## 1. Périmètre honnête

Confluence, c'est vingt ans de développement, des centaines de macros et
l'édition simultanée à plusieurs. « Identique » n'est pas atteignable avec
deux personnes ; ce qui l'est : les 80 % utilisés tous les jours, avec la
même ergonomie. Deux écarts assumés :

- **Pas de choix de police.** Confluence n'en offre pas non plus : la
  hiérarchie passe par les titres (H1-H3), la couleur et l'emphase.
- **Pas d'édition simultanée en temps réel.** Une page est éditée par une
  personne à la fois ; un second éditeur est prévenu (« en cours
  d'édition par … ») au lieu d'écraser le travail.

## 2. Décision de stockage (Q-03 → D-A-035 proposée)

Les pages sont stockées en **arbre JSON de blocs**, jamais en HTML. Le
navigateur les reconstruit avec `el()`/`textContent`. Raisons : la
politique de sécurité du contenu (CSP) interdit les styles en ligne, la
règle de sécurité interdit `innerHTML` sur une donnée du serveur, et un
arbre JSON se valide strictement côté serveur (liste blanche de blocs,
de marques et d'attributs). L'éditeur est un `contenteditable` natif dont
le contenu est converti en JSON à l'enregistrement ; tout ce qui n'est
pas dans la liste blanche est retiré, et l'utilisateur en est averti.

## 3. Structure

**Table 3-1 : Organisation des pages**

| Élément | Choix |
|---|---|
| Espace | Un par projet, mêmes droits lecteur/éditeur que le projet |
| Arbre | Pages parent/enfant, glisser-déposer pour réorganiser, fil d'Ariane |
| Versions | Chaque enregistrement = une version ; comparaison entre deux versions ; restauration |
| Commentaires | En bas de page, avec réponses (même modèle que les tickets) |
| Modèles | Procédure, Instruction de travail, Note de réunion, Compte rendu de revue de conception |
| Recherche | Plein texte FTS5 sur titres et contenu |
| Pièces jointes, images | Images livrées en 0.7.0 (lot noyau v0.4, `core/uploads.py`) ; autres pièces jointes plus tard |
| Check-out / check-in de fichiers | Module Fichiers, plus tard (déjà prévu) |

## 4. Mise en forme (barre d'outils)

Titres H1 à H3 · paragraphe · gras, italique, souligné, barré, code en
ligne · couleur du texte et surlignage (palette fixe) · alignement ·
listes à puces, numérotées, cases à cocher · citation · séparateur ·
tableau (lignes et colonnes, ligne d'en-tête) · bloc de code · lien
externe (http/https seulement) ou lien vers une autre page Dynamite ·
raccourcis clavier usuels (Ctrl+B, Ctrl+I, Ctrl+K…) · commande « / »
pour insérer un bloc ou une macro, comme dans Confluence.

## 5. Macros V1

**Table 5-1 : Macros retenues (les plus utilisées dans Confluence)**

| Macro | Équivalent Confluence | Rôle |
|---|---|---|
| Panneau Info / Note / Avertissement / Succès | Info, Note, Warning, Tip | Encadré coloré avec icône |
| Section repliable | Expand | Détail masqué par défaut |
| Table des matières | Table of Contents | Générée depuis les titres |
| Statut | Status | Pastille colorée (ex. BROUILLON, APPROUVÉ) |
| Date | Date | Date mise en forme |
| Sous-pages | Children Display | Liste automatique des pages enfants |
| Bloc de code | Code Block | Avec étiquette de langage |
| **Ticket Agile** | Jira Issue | Bloc pointant un ticket par sa clé (exigence, tâche, ECN, bogue) |
| **Liste de tickets** | Jira Issues (filtre) | Tableau selon projet, type, statut, label |
| **Matrice Goldmine** | — (propre à la plateforme) | Exigences d'un projet avec « implémentée par » et vérification |

## 6. Bloc « Ticket Agile »

Inséré par la commande « / » ou le bouton Macro, avec la clé connue
(`EQP-4`, `INT-1`…). La clé est vérifiée à l'insertion : si elle
n'existe pas, un message dit pourquoi et comment corriger.

Point de sécurité : le bloc ne montre le contenu du ticket qu'à un lecteur
qui a lui-même accès au projet du ticket. Sinon il affiche « Ticket non
accessible » : une page ne doit jamais faire fuiter un ticket d'un projet
où le lecteur n'a pas de droit.

## 7. Incréments

**Table 7-1 : Plan (chacun : code → test → validation)**

| # | Incrément | Test de sortie |
|---|---|---|
| 1 | Espaces, arbre de pages, versions, lecture | Créer, déplacer, restaurer une version ; lecteur refusé en écriture |
| 2 | ~~Éditeur et mise en forme (§4), validation serveur du JSON~~ — éditeur visuel livré en 0.8.0 (D-B-006) | Contenu hors liste blanche retiré et signalé |
| 3 | Macros de présentation (panneaux, repliable, table des matières, statut, date, sous-pages, code) | Chaque macro rendue, modifiable, versionnée |
| 4 | Ticket Agile, Liste de tickets, Matrice Goldmine | Ticket d'un projet non accessible masqué |
| 5 | Modèles, ~~commentaires~~ (livrés en 0.7.0, D-B-002), recherche | Page créée depuis un modèle ; recherche par mot du contenu |
| 6 | ~~Lot noyau v0.4 et images~~ — livré en 0.7.0 (D-B-003, D-B-004) | Image collée dans une page, servie localement |

C'est le plus gros chantier depuis le début : plusieurs sessions. Le
relais entre comptes (FONDATIONS §11) servira probablement en cours de
route.
