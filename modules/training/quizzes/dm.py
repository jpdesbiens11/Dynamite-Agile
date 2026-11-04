"""Default quizzes of the Diamond topics (0.60.11, D-O-023): the functional tree. Answers in the screen's own texts
(#/diamond/KEY/ftree: intro, legend, panel) and in docs/DECISIONS.md D-O-023."""

DM_01 = """# Quiz : Diamond — l'arbre fonctionnel
pass: 80
## Dans l'arbre fonctionnel, que trouve-t-on à droite d'une fonction ?
- [x] Ses « comment » : les fonctions qui la réalisent
- [ ] Sa raison d'être (« pourquoi ? »)
- [ ] La fonction suivante dans le temps
> De gauche à droite : comment ? De droite à gauche : pourquoi ?, jusqu'à la fonction primaire.
## Dans quel ordre place-t-on les fonctions sœurs, de haut en bas ?
- [ ] Par ordre alphabétique
- [x] Dans l'ordre de la première utilisation, de la sortie de la boîte au service rendu
- [ ] Par importance décroissante
> C'est le « quand ? » de l'arbre ; la dernière branche est gardée pour les fonctions de protection.
## Combien de fonctions primaires un Space peut-il avoir ?
- [x] Une seule
- [ ] Une par sous-système
- [ ] Autant que de fonctions secondaires
## Quelle fonction peut aller au niveau 4, sous une tertiaire ?
- [ ] Une fonction d'estime
- [x] Une fonction technique
- [ ] N'importe quelle fonction d'usage
> L'arbre proprement dit a trois niveaux : primaire, secondaire, tertiaire.
## On archive F12. Que devient le numéro F12 ?
- [ ] Il est redonné à la prochaine fonction créée
- [x] Il reste pris pour toujours, pour le suivi dans le DFMEA, les requirements et les essais
- [ ] Il passe à la fonction suivante, F13
> Ses « comment » prennent sa place sous sa fonction parente.
## Comment montre-t-on le chemin critique de conception ?
- [x] En cochant « Chemin critique » : la flèche devient épaisse
- [ ] Avec une flèche pointillée
- [ ] En plaçant la fonction hors arbre
> La flèche pointillée relie une fonction de contrôle à ce qu'elle contrôle (rétroaction).
## Où va une fonction d'estime, comme « Plaire par une allure épurée » ?
- [ ] Toujours au niveau 2, comme sous-système
- [x] Le plus souvent hors de l'arbre, notée au CdCF
- [ ] Au niveau 4, sous une tertiaire
## Comment fait-on d'une fonction l'un des « comment » d'une autre, à la souris ?
- [x] On glisse sa boîte sur l'autre boîte
- [ ] On double-clique sur les deux boîtes
- [ ] On l'archive puis on la recrée
> Au clavier : Alt + flèches sur une boîte sélectionnée.
## Que fait Alt + ↑ sur une fonction sélectionnée ?
- [ ] Elle remonte d'un niveau, vers la gauche
- [x] Elle passe plus tôt dans sa branche (« quand »)
- [ ] Elle devient la fonction primaire
## On retire une fonction de l'arbre. Que deviennent ses « comment » ?
- [x] Ils la suivent hors de l'arbre, attachés à elle
- [ ] Ils sont archivés
- [ ] Ils remontent sous la fonction primaire
## Le panneau affiche « Pourquoi ? Pour Produire une lumière réglable (F12) ». Qu'est-ce que cette lecture vérifie ?
- [x] Que la fonction répond bien à un « comment » de sa fonction parente
- [ ] Que la fonction a un essai dans Testing
- [ ] Que la fonction est sur le chemin critique
> On relit l'arbre de gauche à droite (comment ?) et de droite à gauche (pourquoi ?) pour vérifier sa cohérence.
"""

DM_02 = """# Quiz : Diamond — la structure fonctionnelle
pass: 80
## Dans la structure fonctionnelle, où se placent les entrées du système ?
- [x] À gauche, hors du cadre du système
- [ ] À droite, après les sous-systèmes
- [ ] Au centre, dans le cadre de la fonction primaire
> Les entrées à gauche, les sorties à droite, et le cadre du système (la fonction primaire) entre les deux.
## Que deviennent les fonctions secondaires dans la vue générale ?
- [x] Les sous-systèmes du produit
- [ ] Les entrées du système
- [ ] Des fonctions techniques
## Quels sont les trois types de flux de la légende ?
- [x] Énergie, matière, information
- [ ] Électrique, mécanique, logiciel
- [ ] Principal, secondaire, rétroaction
## Que montre la vue détaillée ?
- [ ] Les fonctions techniques de chaque tertiaire
- [x] Les fonctions tertiaires dans le cadre de leur sous-système, et les flux qu'elles traitent
- [ ] Seulement les entrées et les sorties
> Aucune fonction technique : ce niveau de détail n'appartient pas à la conception système.
## Un flux de la vue générale va de F5 à F12. Qu'attend-on dans la vue détaillée ?
- [x] Le même type de flux, d'une tertiaire de F5 à une tertiaire de F12
- [ ] Rien : les deux vues sont indépendantes
- [ ] Un flux de F12 vers F5
> Les flux de la structure générale doivent toujours être présents dans la vue de détails.
## Un bloc n'échange aucun flux. Qu'est-ce que cela signale ?
- [x] Souvent une incohérence de l'arbre : la fonction est à reformuler, à rattacher ou à retirer
- [ ] Rien, c'est normal pour une fonction de protection
- [ ] Il faut le transformer en entrée du système
## Peut-on tracer un flux directement d'une entrée à une sortie ?
- [ ] Oui, s'il est de type information
- [x] Non : il doit traverser la fonction qui le traite
- [ ] Oui, dans la vue générale seulement
## Comment trace-t-on un flux à la souris ?
- [x] On choisit le bloc de départ, puis « Relier en cliquant la cible » et on clique le bloc d'arrivée
- [ ] On double-clique entre deux blocs
- [ ] On glisse une boîte sur une autre
> Glisser une boîte la déplace ; le panneau propose aussi une liste « Vers ».
## « Courant », « chaleur », « consigne » : qu'est-ce que c'est sur le schéma ?
- [x] Les libellés des flux
- [ ] Des fonctions tertiaires
- [ ] Des sous-systèmes
## On efface une entrée du système. Que deviennent ses flux ?
- [x] Ils sont effacés avec elle, dans les deux vues
- [ ] Ils sont rattachés à une autre entrée
- [ ] Ils restent, sans origine
"""

DM_03 = """# Quiz : Diamond — l'analyse de risque projet
pass: 80
## Comment s'écrit un risque dans le registre ?
- [x] Si <cause>, alors <événement>, ce qui <conséquence>
- [ ] Un mot-clé, comme « Délais »
- [ ] Le nom de la personne responsable
## Comment se calcule le score d'un risque ?
- [ ] Probabilité + impact
- [x] Probabilité × impact, chacun de 1 à 5
- [ ] Impact × détection
> Le score va de 1 à 25 : Faible (1 à 4), Moyen (5 à 9), Élevé (10 à 14), Critique (15 à 25).
## Un risque a une probabilité 3 et un impact 5. Quel est son niveau ?
- [ ] Moyen
- [ ] Élevé
- [x] Critique
> 3 × 5 = 15, le seuil de Critique.
## Quelles sont les quatre stratégies de réponse ?
- [x] Éviter, réduire, transférer, accepter
- [ ] Ignorer, reporter, déléguer, annuler
- [ ] Prévenir, détecter, corriger, documenter
## Que montre le risque résiduel ?
- [x] Le score attendu une fois l'action réalisée
- [ ] Le score du risque le plus grand du registre
- [ ] Les risques fermés
## Que signale le registre pour un risque élevé sans responsable ?
- [x] Un conseil : action ou responsable manquant
- [ ] Rien, c'est permis
- [ ] Le risque est archivé
## À quoi sert la case « À détailler dans le DFMEA » ?
- [x] Marquer un risque technique à reprendre fonction par fonction dans le DFMEA
- [ ] Fermer le risque
- [ ] Le transférer à un fournisseur
> L'analyse de risque projet est vue de haut ; le DFMEA détaille modes de défaillance, causes et contrôles.
## On archive R-4. Que devient le numéro R-4 ?
- [ ] Il est redonné au prochain risque
- [x] Il reste pris pour toujours
- [ ] Il passe à R-5
## Que fait un clic sur une case de la carte des risques ?
- [x] Il filtre le registre sur cette probabilité et cet impact
- [ ] Il crée un risque
- [ ] Il change le score des risques de la case
## Un risque critique est « accepté ». Qu'attend la méthode ?
- [x] Une justification dans les notes : pourquoi on vit avec
- [ ] Rien de plus
- [ ] Qu'il soit archivé tout de suite
"""

DM_04 = """# Quiz : Diamond — le DFMEA (AIAG-VDA)
pass: 80
## Quels sont les trois niveaux de la structure d'un DFMEA AIAG-VDA ?
- [x] Higher-Level Element, Focus Element, Lower-Level Element
- [ ] Système, logiciel, matériel
- [ ] Besoin, requirement, essai
## Sur quel niveau se lit le Failure Effect, coté par la sévérité (S) ?
- [x] Higher-Level Element : l'utilisateur, le produit ou le système
- [ ] Focus Element
- [ ] Lower-Level Element
## D'où vient la colonne « Function of Focus Element » ?
- [x] De l'arbre fonctionnel de Diamond, fonction par fonction
- [ ] D'une liste fixe de fonctions génériques
- [ ] Elle s'écrit librement à chaque ligne
## Où travaille-t-on pour éviter la défaillance (en-têtes orange) ?
- [ ] Higher-Level Element et Failure Effect
- [x] Lower-Level Element : Failure Cause, Prevention et Detection Controls
- [ ] Focus Element et Requirement
## Comment se calcule le RPN ?
- [x] S × O × D, de 1 à 1000
- [ ] S + O + D, de 3 à 30
- [ ] Le plus grand des trois
## Pourquoi l'AP plutôt que le RPN ?
- [x] L'AP lit d'abord la sévérité : un effet grave n'est pas noyé par une bonne détection
- [ ] L'AP est plus précis parce qu'il va jusqu'à 1000
- [ ] L'AP ne tient pas compte de l'occurrence
> S 1, O 10, D 10 donne RPN 100 mais AP Low ; S 9, O 4, D 1 donne RPN 36 mais AP Medium.
## Une ligne a S 9, O 6, D 1. Quel est son AP ?
- [x] High
- [ ] Medium
- [ ] Low
> S 9-10 avec O 6-7 : High, quelle que soit la détection.
## Que demande un AP High ?
- [x] Une action pour améliorer la prévention ou la détection, ou la justification des contrôles actuels
- [ ] Rien de plus qu'un AP Low
- [ ] L'archivage de la ligne
## La prévention agit sur quelle cote ?
- [x] L'occurrence (O)
- [ ] La sévérité (S)
- [ ] La détection (D)
> Les contrôles de détection agissent sur D ; seule une modification de la conception change S.
## Comment déplacer une ligne du DFMEA au clavier ?
- [x] Alt + ↑ ou Alt + ↓ dans une de ses cellules
- [ ] Ctrl + X puis Ctrl + V
- [ ] On ne peut pas la déplacer
## Que fait « Depuis les risques » ?
- [x] Ajoute une ligne par risque projet coché « À détailler dans le DFMEA »
- [ ] Copie tout le registre de risques
- [ ] Ferme les risques projet
"""

DM_05 = """# Quiz : Diamond — Golden Nuggets
pass: 80
## Que veut dire raisonner « à partir des premiers principes » ?
- [x] Ramener le problème à ce que la physique et les coûts imposent, puis reconstruire la solution
- [ ] Copier la solution du meilleur concurrent
- [ ] Suivre les normes de l'industrie sans les questionner
## Quelle est la première étape de l'algorithme en cinq étapes ?
- [x] Rendre les exigences moins bêtes
- [ ] Automatiser
- [ ] Simplifier et optimiser
## Dans quel ordre vient l'automatisation ?
- [ ] En premier, pour gagner du temps
- [ ] En troisième
- [x] En dernier, après avoir supprimé, simplifié et accéléré
> Automatiser trop tôt, c'est automatiser une pièce ou un procédé qu'il aurait fallu supprimer.
## Pourquoi chaque exigence doit-elle porter le nom d'une personne ?
- [x] Pour pouvoir lui demander pourquoi, et remettre l'exigence en question avec elle
- [ ] Pour savoir qui blâmer en cas d'échec
- [ ] Parce que la norme l'exige
## « La meilleure pièce est celle qu'on n'a pas. » Qu'est-ce que cela donne dans le DFMEA ?
- [x] Un mode de défaillance disparaît pour de bon quand la pièce disparaît
- [ ] Il faut ajouter un contrôle de détection par pièce
- [ ] La sévérité baisse automatiquement
## Le bloc d'alimentation externe de la lampe applique quel principe ?
- [x] Sortir la partie gênante (extraction)
- [ ] Inverser
- [ ] Agir par impulsions
## Une pièce qui ne se monte que dans le bon sens applique quel principe ?
- [x] L'asymétrie (détrompage)
- [ ] La segmentation
- [ ] La copie bon marché
## Que montre l'exemple du coût des matières d'une batterie ?
- [x] L'écart entre le prix et les matières vient de la fabrication, donc il peut se réduire
- [ ] Les batteries ne peuvent pas coûter moins cher
- [ ] Il faut toujours acheter le moins cher
## La gradation des DEL par MLI applique quel principe ?
- [x] Agir par impulsions (action périodique)
- [ ] Qualité locale
- [ ] Intermédiaire
## Que dit la règle « essayer tôt, jusqu'à la rupture » ?
- [x] Un essai qui casse apprend plus qu'une analyse qui rassure
- [ ] Il ne faut tester que le produit final
- [ ] Un prototype ne doit jamais casser
"""
