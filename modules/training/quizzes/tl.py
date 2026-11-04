"""Quizzes TL-01 to TL-03 and TL-06 (0.50.10, D-B-128): the design methods of Tools and Generator; every answer is
in their page / FAQ of the TOOLS wiki (methods_*.py) or in the Help chapter (TL-04 and TL-05 are retired topics)."""

TL_01 = """# Quiz : Idéation et brainwriting
pass: 80
## Quelles sont les règles du brainstorming ?
- [x] Pas de critique pendant la production
- [x] La quantité d'abord ; les idées folles sont bienvenues
- [x] Rebondir sur les idées des autres
- [ ] Voter après chaque idée
## Comment formule-t-on la question d'une séance ?
- [x] « Comment pourrions-nous… ? »
- [ ] « Pourquoi le design actuel est-il mauvais ? »
- [ ] « Quelle est la meilleure solution ? »
## Combien d'idées viser en 30 minutes à 6 personnes ?
- [ ] Une dizaine, bien argumentées dès le départ
- [x] Au moins 50
- [ ] 108 : 6 personnes × 3 idées × 6 tours
> La quantité fait émerger la qualité. 108, c'est le brainwriting 6-3-5.
## Que veut dire « 6-3-5 » ?
- [x] 6 personnes, 3 idées, 5 minutes par tour
- [ ] 6 tours, 3 personnes, 5 idées
- [ ] 6 minutes, 3 tours, 5 personnes
> 108 idées en 30 minutes, en silence.
## Une ou deux voix dominent le brainstorming. Que faire ?
- [x] Passer au brainwriting, silencieux et écrit
- [ ] Demander aux autres de parler plus fort
- [ ] Arrêter la séance
## Dans l'outil, comment les paires du brainwriting changent-elles ?
- [x] Chacun rencontre chacun en n − 1 tours (rotation « toutes rondes »)
- [ ] Au hasard à chaque tour, avec parfois le même partenaire
- [ ] L'animateur forme les paires à chaque tour
## Le nombre de participants est impair. Que fait l'outil ?
- [x] Il forme un trio à chaque tour, c'est normal
- [ ] Il refuse de démarrer
- [ ] Il laisse une personne seule
## Pendant les tours, qui voit quoi ?
- [x] Ses idées et celles de ses partenaires ; tout, à la revue
- [ ] Toutes les idées de tous, en direct, dès le premier tour
- [ ] Ses propres idées seulement, jusqu'à la revue
## Quand juge-t-on les idées ?
- [ ] Pendant chaque tour
- [x] À la revue, avec les étoiles ★
- [ ] Jamais : on les garde toutes telles quelles
## Qui peut mettre des étoiles ★ à une idée ?
- [x] Tout membre, autant qu'il veut
- [ ] L'animateur seulement, à la revue
- [ ] Chacun trois étoiles par séance
## Quelle est la colonne vertébrale d'un storytelling ?
- [x] Il était une fois… / Chaque jour… / Jusqu'au jour où… / … / Depuis ce jour…
- [ ] Contexte… / Problème… / Cause racine… / Solution… / Bénéfice…
- [ ] Qui… / Quoi… / Où… / Quand… / Comment… / Pourquoi…
## Une histoire n'a pas de « jusqu'au jour où ». Conséquence ?
- [x] Pas de problème, donc pas d'idée
- [ ] Elle est plus claire
- [ ] Elle devient un requirement directement
## Comment passe-t-on d'une histoire aux requirements ?
- [x] Chaque douleur devient un need, d'où dérivent des requirements
- [ ] Chaque phrase de l'histoire devient un requirement
- [ ] L'histoire entière devient le statement d'un requirement
## Dans la Mind Map de l'outil, comment relie-t-on deux cartes ?
- [x] « Lier » une carte, puis cliquer sur l'autre
- [ ] Glisser une carte sur l'autre
- [ ] Double-cliquer sur la surface entre les deux
> Double-cliquer sur la surface pose une carte.
## Après la divergence, où envoie-t-on les meilleures idées ?
- [x] Vers une Pugh Matrix
- [ ] Directement en ECN
- [ ] Dans le backlog Agile, sans tri
"""

TL_02 = """# Quiz : Matrice de Pugh
pass: 80
## Quelles notes met-on dans une Pugh Matrix classique ?
- [x] +, S ou −, par rapport au Datum
- [ ] Une note de 1 à 10, multipliée par un poids
- [ ] Oui ou non : le concept respecte-t-il le criterion ?
## Que vaut la colonne du Datum ?
- [x] « S » partout, par définition
- [ ] « + » partout
- [ ] Elle n'est pas notée et ne s'affiche pas
## Quels totaux donne la matrice par concept ?
- [x] Σ+, ΣS, Σ−, net et rang
- [ ] Une moyenne pondérée et un rang
- [ ] Σ+ et Σ− seulement
## Comment lire les totaux ?
- [x] Ne pas choisir au net seulement : regarder les − forts
- [ ] Prendre le net le plus élevé, sans discussion
- [ ] Prendre le concept avec le moins de S
## Pourquoi la Pugh classique n'a-t-elle pas de poids ?
- [x] Elle sert à comprendre et améliorer les concepts, pas à calculer un gagnant
- [ ] Parce que les criteria viennent de Goldmine, déjà classés par criticité
- [ ] Parce que le Datum sert de poids pour tous les criteria
> Les poids viennent ensuite, avec Kepner-Tregoe.
## Des criteria sont éliminatoires. Quelle méthode choisir ?
- [ ] Pugh, en mettant des poids en douce
- [x] Kepner-Tregoe (DOIT éliminatoires, VEUT pondérés)
- [ ] Le brainstorming
## Combien de concepts compare-t-on en général ?
- [ ] 1 ou 2
- [x] 3 à 8
- [ ] Plus de 20
## D'où viennent les criteria dans l'outil ?
- [x] De Goldmine : needs, requirements, une Life-Cycle Phase ou une category
- [ ] De la Test Base : un criterion par test
- [ ] Des idées étoilées de la séance d'Idéation
## Qu'est-ce qu'un nouveau tour ?
- [x] Une copie sans notes autour d'un nouveau Datum
- [ ] Une copie avec les mêmes notes et le même Datum
- [ ] Une nouvelle matrice avec de nouveaux criteria
> Le nouveau Datum est souvent le meilleur concept du tour d'avant.
## Le Datum est mal choisi. Quel symptôme ?
- [x] Tout devient + ou tout devient −
- [ ] Les totaux ne se calculent plus
- [ ] La matrice se bloque
## Pourquoi éviter des criteria redondants ?
- [x] Ils comptent deux fois la même chose
- [ ] L'outil les refuse
- [ ] Ils rendent l'export Excel impossible
## Quand s'arrête-t-on de faire des tours ?
- [x] Quand un concept domine, ou que les − restants sont acceptés
- [ ] Après exactement 5 tours, quel que soit le résultat
- [ ] Quand chaque concept a au moins un +
## Comment ajouter une note à une case quand ce n'est pas évident ?
- [x] Double-clic sur la case
- [ ] Un commentaire Dynamite
- [ ] Ce n'est pas possible
## Que devient une matrice décidée ?
- [x] Elle passe en lecture seule jusqu'à ce qu'on la rouvre
- [ ] Elle part en Kepner-Tregoe automatiquement
- [ ] Elle reste modifiable par son créateur seulement
## Peut-on prendre « tous les Needs » comme criteria ?
- [x] Oui : c'est souvent le meilleur premier tour
- [ ] Non : seulement des requirements
- [ ] Seulement avec un seul need
"""

TL_03 = """# Quiz : Kepner-Tregoe (Decision Analysis)
pass: 80
## Une alternative ne passe pas un DOIT. Que devient-elle ?
- [x] Elle est éliminée
- [ ] Elle perd 10 points
- [ ] Elle reste, avec un avertissement
## Comment se calcule le score pondéré d'une alternative ?
- [x] Σ (poids × note) sur les VEUT
- [ ] La moyenne des notes
- [ ] Le nombre de DOIT passés
## Deux VEUT : Specific Energy (poids 10) et Cost (poids 5). L'alternative A a 8 et 6. Son score ?
- [ ] 14
- [x] 110
- [ ] 70
> 10 × 8 + 5 × 6 = 80 + 30 = 110.
## Que veut dire une note de 10 sur un VEUT ?
- [x] L'alternative est la meilleure sur ce souhait
- [ ] Le souhait est le plus important
- [ ] Le souhait est obligatoire
## Après les scores, que fait-on pour les 2 ou 3 meilleures alternatives ?
- [x] On liste leurs risques, avec probabilité et gravité
- [ ] On les compare à un Datum, en +, S, −
- [ ] Rien : le meilleur score l'emporte
## Quel est le piège classique avec les DOIT ?
- [x] Mettre un souhait en DOIT
- [ ] Mettre un poids sur un DOIT
- [ ] Lier un DOIT à un requirement Goldmine
## Que faut-il fixer avant de noter les alternatives ?
- [x] Les poids des VEUT
- [ ] Les risques de chaque alternative
- [ ] Le Datum
## Quelle est la différence avec Pugh ?
- [x] Pugh explore sans poids ; Kepner-Tregoe tranche entre finalistes
- [ ] Pugh tranche entre finalistes ; Kepner-Tregoe explore
- [ ] Pugh pondère les criteria ; Kepner-Tregoe ne les pondère pas
## Comment énoncer la décision ?
- [x] « Choisir … pour … »
- [ ] « Comment pourrions-nous… ? »
- [ ] « Pourquoi … ? »
## Un DOIT peut-il venir de Goldmine ?
- [x] Oui, d'un requirement ou d'un need
- [ ] Non, il est toujours tapé à la main
- [ ] Oui, mais seulement d'un test de la Test Base
## L'outil couvre-t-il l'analyse de problème (EST / N'EST PAS) ?
- [x] Non, l'analyse de décision seulement
- [ ] Oui, avec l'analyse de décision
- [ ] Oui, dans un onglet à part de la même décision
## Que se passe-t-il quand on clique « Décider » ?
- [x] Le choix et sa justification sont figés jusqu'à réouverture
- [ ] La décision part au CCB pour approbation
- [ ] Les alternatives perdantes sont retirées
## Quel piège concerne le gagnant ?
- [x] Ignorer ses risques
- [ ] Le noter trop haut
- [ ] Le comparer au Datum
"""

TL_06 = """# Quiz : Generator — références documentaires du PDP
pass: 80
## Sur quoi sont rangés les types de documents de Generator ?
- [x] Les quatre phases du PDP : Discovery, Concept, Design, Validation et lancement
- [ ] Les chapitres d'une norme
- [ ] L'ordre alphabétique seulement
## Quel livrable termine la phase A. Discovery ?
- [x] Le Lean Canvas et les hypothèses à tester (LCV)
- [ ] Le Validation Report
- [ ] La Critical Design Review
## Quelle revue termine la phase B. Concept ?
- [x] La Concept Review (CRV)
- [ ] Le Lean Canvas
- [ ] Le Validation Report
## À quelle étape du PDP range-t-on le CdCF ?
- [x] 11 — Définition des spécifications d'ingénierie
- [ ] 03 — Définition du projet
- [ ] 21 — Tests de validation
## Quel livrable termine la phase D. Validation et lancement ?
- [ ] La Preliminary Design Review
- [x] Le Validation Report (VVR : vérification et validation)
- [ ] Le CdCF
## Que décide-t-on au bilan Build-Measure-Learn d'un MVP ?
- [x] Persévérer ou pivoter, selon ce que les mesures ont appris
- [ ] Le nom de fichier du rapport
- [ ] La couleur du thème
## Comment est formée une référence ?
- [x] TYPE-DDDDD-TTTTT : le type puis la date-heure série Excel en UTC
- [ ] Un compteur par Space
- [ ] Les initiales de l'auteur et la date
## Qui donne le numéro final d'une référence ?
- [x] Le serveur, à la réservation
- [ ] Le navigateur, dans l'aperçu
- [ ] Le premier qui enregistre le fichier
> L'aperçu suit l'horloge du poste ; le serveur garantit qu'un numéro n'est donné qu'une fois.
## Une référence réservée par erreur…
- [ ] Est supprimée du registre
- [x] Est annulée par un administrateur, jamais supprimée
- [ ] Est réutilisée par la prochaine réservation
## Que remplace le code système, s'il est rempli ?
- [x] Le libellé de l'étape dans le dossier
- [ ] Le type de document
- [ ] Le numéro de la référence
## Où retrouve-t-on toutes les références d'un Space ?
- [x] Dans le Registre (Tools → Generator → Registre), exportable en CSV
- [ ] Dans Goldmine
- [ ] Dans la feuille de temps
"""
