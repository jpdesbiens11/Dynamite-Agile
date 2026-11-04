"""Quizzes KB-01 to KB-03 (0.50.10, D-B-128; generic since 0.60.01): the knowledge base pages -- Definitions and
Acronyms, Getting Things Done, Product Function Structure (F-XX)."""

KB_01 = """# Quiz : Definitions et Acronyms de l'outil
pass: 80
## Comment formule-t-on une fonction d'usage ?
- [x] Un verbe d'action suivi d'un complément
- [ ] Un verbe d'état qui exprime un caractère passif
- [ ] Le nom de la pièce qui la réalise
> Ex. « Fondre un bâtonnet de colle ». Les fonctions d'estime prennent plutôt un verbe d'état (« être sécuritaire »).
## Une fonction d'estime…
- [x] Traduit une considération du client, souvent avec un verbe d'état
- [ ] Est toujours une contrainte imposée par une norme
- [ ] Dépend d'un concept technique précis
## Une fonction technique…
- [ ] Est la fonction principale du produit
- [x] Dépend d'un concept ; on la garde dans les notes à la conception
- [ ] Est toujours supprimée de l'analyse
## Une spécification fonctionnelle…
- [x] Est mesurable et ne dépend pas du concept retenu
- [ ] Décrit la solution technique choisie
- [ ] Remplace la fonction dans l'arbre fonctionnel
## Dans un requirement, que veut dire « shall » ?
- [x] Obligatoire
- [ ] Recommandé
- [ ] Permis
> should = recommandé (objectif), may = permis, will = fait ou intention.
## Dans un requirement, que veut dire « will » ?
- [ ] Obligatoire
- [ ] Recommandé (objectif)
- [x] Un fait ou une intention
- [ ] Permis
## Que désigne l'acronyme CdCF ?
- [x] Le cahier des charges fonctionnel
- [ ] Le compte rendu de conception finale
- [ ] Le calendrier de fabrication
## Que désigne l'acronyme RVE ?
- [ ] Le rapport de vérification électrique
- [x] Le rapport de validation expérimentale
- [ ] La revue de conception
## Que désigne IADT pour un requirement ?
- [x] Les méthodes de vérification : Inspection, Analysis, Demonstration, Test
- [ ] Les quatre phases du PDP
- [ ] Les niveaux de criticité
## Où modifie-t-on une definition ou un acronym ?
- [x] Testing → Listes centrales (Admin du Space TESTING ou administrateur)
- [ ] Directement dans la page Definitions de la BDC
- [ ] Dans le fichier Word exporté
> La page de la BDC est régénérée depuis la liste ; une modification manuelle y arrête la mise à jour.
## À quoi sert la table de nomenclature des definitions ?
- [x] Relier un terme de l'équipe au terme d'une norme citée qu'il remplace
- [ ] Traduire tous les termes en anglais
- [ ] Classer les acronymes par domaine
## Les termes techniques de l'outil sont…
- [x] En anglais, avec leur équivalent français dans la page de traduction
- [ ] En français seulement
- [ ] Dans la langue choisie par chaque Space
"""

KB_02 = """# Quiz : Getting Things Done — les principes
pass: 80
## Une action prend moins de 2 minutes. Que faire ?
- [x] La faire maintenant, quand vous y pensez
- [ ] La noter dans l'Inbox pour la Weekly Review
- [ ] La mettre au calendrier
> L'organiser coûterait plus cher que la faire.
## Que met-on au calendrier, selon nos pépites ?
- [x] Seulement le travail d'équipe (réunions, CCB Reviews, essais réservés)
- [ ] Toutes ses tasks, une plage réservée pour chacune
- [ ] Les tasks de plus de 2 heures seulement
## Combien d'éléments au plus dans une liste qui reste relue ?
- [ ] 5
- [x] 20, avec un status
- [ ] 50
## Comment avoir la bonne liste au Test Bench ?
- [x] Un label de contexte (@banc) et le filtre « Mes éléments »
- [ ] Un sprint Agile dédié aux essais au banc
- [ ] Une page Dynamite « À faire au banc » mise à jour chaque matin
## Vous ne savez pas quoi faire. Dans quel ordre choisir, selon David Allen ?
- [x] Contexte, temps disponible, énergie, puis priority
- [ ] Priority, puis temps disponible, puis contexte
- [ ] Échéance, puis priority, puis énergie
## Quand planifie-t-on et quand fait-on la Weekly Review ?
- [x] Planifier le lundi ; Weekly Review le vendredi
- [ ] Planifier le vendredi ; Weekly Review le lundi
- [ ] Les deux le lundi matin, avant le Dashboard
## Quelle durée viser pour une task ?
- [ ] Une semaine au plus, idéalement 2 jours
- [x] Une demi-journée au plus, idéalement moins de 2 heures
- [ ] Moins de 2 minutes, sinon c'est un projet
## « Qualifier l'élément chauffant » est…
- [x] Un projet (il faut le découper en tasks)
- [ ] Une task
- [ ] Un élément Someday / Maybe
> Une task : « Écrire la Test Procedure de rigidité diélectrique ».
## Quelles sont les cinq étapes de GTD ?
- [x] Capturer, Clarifier, Organiser, Revoir, Faire
- [ ] Planifier, Exécuter, Vérifier, Agir, Clore
- [ ] Lister, Trier, Déléguer, Faire, Archiver
## Sur la plateforme, que représente une Epic ?
- [x] Un projet
- [ ] Une Next Action
- [ ] Un élément de référence
## Sur la plateforme, que représente un ticket assigné à vous ?
- [x] Une Next Action
- [ ] Un élément Waiting For
- [ ] Un élément Someday / Maybe
## Un requirement en « Customer Clarification » est, pour vous…
- [x] Un « Waiting For »
- [ ] Une Next Action
- [ ] Une référence
## À quoi correspond le backlog, en GTD ?
- [x] À la liste Someday / Maybe
- [ ] Aux Next Actions
- [ ] À la liste Waiting For
## Quelle règle s'applique à chaque projet en cours ?
- [x] Il a au moins une Next Action
- [ ] Il a une réunion hebdomadaire
- [ ] Il a au plus 5 tasks
"""

KB_03 = """# Quiz : Structure des fonctions du produit (F-XX)
pass: 80
## D'où viennent les fonctions F-XX de la liste centrale ?
- [x] De l'analyse fonctionnelle du produit de l'équipe
- [ ] D'un catalogue fourni par une norme
- [ ] Des tickets Agile
## Quel code est valide pour une fonction ?
- [x] F12
- [ ] FN-12-A
- [ ] 12F
> F suivi de 1 à 3 chiffres ; une sous-fonction est permise (F35.1).
## Qui ajoute ou désactive une fonction de la liste centrale ?
- [x] Un Admin du Space TESTING ou un administrateur
- [ ] Tout éditeur d'un Space
- [ ] Seulement l'auteur du requirement
## Une fonction déjà utilisée par un test…
- [ ] Est supprimée avec ses liens
- [x] Est désactivée : elle reste sur ses éléments mais n'est plus offerte
- [ ] Ne peut plus être renommée
## Dans l'arbre fonctionnel, que répond une fonction secondaire ?
- [x] Au « comment ? » de la fonction principale
- [ ] Au « pourquoi ? » de la fonction tertiaire
- [ ] Au « combien ? » du cahier des charges
## Les fonctions secondaires mènent surtout à…
- [x] L'identification des sous-systèmes du produit
- [ ] La liste des fournisseurs
- [ ] Le choix des couleurs
## Où un requirement Goldmine indique-t-il ses fonctions ?
- [x] Dans le champ « Functions » de sa fiche
- [ ] Dans son titre
- [ ] Dans le champ Allocation seulement
## Pourquoi relier un test à une fonction ?
- [x] Deux tests peuvent vérifier un même requirement sur deux fonctions différentes
- [ ] Pour calculer le coût du test
- [ ] Pour choisir le laboratoire
## Que contient la page BDC « Product Function Structure (F-XX) » ?
- [x] La liste active des fonctions et leurs composants, régénérée depuis la liste centrale
- [ ] Les comptes rendus de réunion
- [ ] Le CdCF complet
## Dans « Test Procedure » d'un requirement, quels tests viennent en premier ?
- [x] Ceux des mêmes fonctions que le requirement
- [ ] Les plus récents
- [ ] Ceux du catalogue TESTING seulement
"""
