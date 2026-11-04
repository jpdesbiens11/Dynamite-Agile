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
