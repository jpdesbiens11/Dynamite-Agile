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
