"""Quizzes RH-01 and RH-02 (0.50.10, D-B-128): the personal follow-up of the account menu -- « Mes objectifs » and the
annual review (core/objectives.py, core/reviews.py), the internship evaluation, the professional profile
(core/profile.py) and « Mon équipe » (core/team.py)."""

RH_01 = """# Quiz : Mes objectifs et évaluation annuelle
pass: 80
## Quelles sont les trois étapes de l'évaluation annuelle ?
- [x] Début d'année, Mi-année, Fin d'année
- [ ] Objectifs, Formation, Salaire
- [ ] Janvier, Juin, Décembre, à dates fixes
## Quand l'étape suivante s'ouvre-t-elle ?
- [x] Quand l'employé et son gestionnaire ont signé
- [ ] Dès que l'employé a signé
- [ ] Dès que le gestionnaire a signé
## Que convient-on au Début d'année ?
- [x] Les objectifs annuels, de développement et de formation
- [ ] Seulement les objectifs de formation
- [ ] Le verdict de l'année précédente
## Que demande la Mi-année ?
- [x] Sur chaque item, un commentaire de l'employé et un du gestionnaire
- [ ] Un seul commentaire global du gestionnaire
- [ ] Une note de 1 à 10 par item
## Que demande la Fin d'année ?
- [x] Un verdict du gestionnaire sur chaque item (l'employé peut donner son auto-évaluation)
- [x] Un commentaire général de chaque côté
- [ ] La validation du Journal d'audit
## D'où viennent les items de l'évaluation ?
- [x] Des objectifs de l'année
- [x] Des items du plan de formation (Training)
- [ ] Des tickets Agile fermés
## Une étape signée est-elle modifiable ?
- [x] Non ; le gestionnaire peut la rouvrir
- [ ] Oui, par l'employé, jusqu'à la fin de l'année
- [ ] Non ; un administrateur peut la rouvrir
## Qui voit vos objectifs et votre évaluation ?
- [x] Vous et votre gestionnaire seulement
- [ ] Vous, votre gestionnaire et les administrateurs
- [ ] Vous, votre gestionnaire et les Admin de vos Spaces
## Que garde le journal d'audit d'une évaluation ?
- [x] Qui a fait quoi et quand, sans le texte
- [ ] Qui a fait quoi, avec le texte des commentaires
- [ ] Rien : l'évaluation n'est pas journalisée
## Quand l'année peut-elle être fermée ?
- [x] Une fois la Fin d'année signée par les deux
- [ ] À tout moment par l'employé
- [ ] Le 31 décembre automatiquement
## Que fait la fermeture de l'année ?
- [x] Elle archive l'année et reporte les objectifs de développement choisis
- [ ] Elle archive l'année et reporte tous les objectifs annuels
- [ ] Elle efface les objectifs pour repartir de zéro
## Comment se mesure un objectif de développement ?
- [x] Par un niveau cible sur une échelle de 5 marches
- [ ] Par un pourcentage d'avancement seulement
- [ ] Par le nombre d'heures de formation
## Qui fixe le niveau cible et les attentes d'un objectif de développement ?
- [x] Le gestionnaire
- [ ] L'employé
- [ ] Un administrateur
## Qui est « votre gestionnaire » pour l'évaluation ?
- [x] La personne choisie dans menu à votre nom → Paramètres
- [ ] L'administrateur qui a créé votre compte
- [ ] L'Admin de votre Space principal
## Vous signez une étape. Comment votre gestionnaire le sait-il ?
- [x] Un message arrive dans son Dashboard → Messages
- [ ] Par courriel
- [ ] Il doit vérifier lui-même chaque jour
"""

RH_02 = """# Quiz : Évaluation de stage, profil professionnel et Mon équipe
pass: 80
## Quelles sont les étapes de l'évaluation d'un stagiaire ?
- [x] Accueil, Mi-stage, Évaluation finale
- [ ] Début d'année, Mi-année, Fin d'année
- [ ] Entrevue, Contrat, Départ
## Comment la grille de compétences d'un stagiaire est-elle notée ?
- [x] De 1 à 4, avec une recommandation
- [ ] De 1 à 5, comme les objectifs de développement
- [ ] Réussi / échoué, compétence par compétence
## Quelle durée de stage le profil accepte-t-il ?
- [ ] 1 à 2 mois
- [x] 4 à 8 mois
- [ ] 12 mois exactement
## Quels champs du profil sont fixés par le gestionnaire ?
- [x] Le type (employé / stagiaire), le titre, le niveau d'expérience, la date d'embauche
- [x] Pour un stagiaire : les dates de stage, l'école, le programme, le tuteur
- [ ] La formation et les expériences de l'employé
## Qu'écrit l'employé dans son profil ?
- [x] Son parcours : formation, expériences, compétences, langues
- [ ] Son titre, son niveau et sa date d'embauche
- [ ] Ses objectifs de l'année et son plan de formation
## Où le profil est-il affiché ?
- [x] En tête de chaque page d'évaluation
- [ ] Sur l'Accueil, pour tous les employés
- [ ] Dans l'annuaire « Qui contacter ? »
## Qui voit votre profil professionnel ?
- [x] Vous et votre gestionnaire seulement
- [ ] Tous les membres de vos Spaces
- [ ] Les administrateurs
## Qui apparaît dans « Mon équipe » ?
- [x] Les personnes qui vous ont choisi comme gestionnaire
- [ ] Les membres des Spaces dont vous êtes Admin
- [ ] Les comptes que vous avez créés ou dupliqués
## Que montre la carte d'une personne dans « Mon équipe » ?
- [x] Ses 3 étapes, qui a signé, et ce qui vous attend
- [ ] Ses heures de la semaine et ce qui reste à approuver
- [ ] Ses tickets en retard et ses Messages non lus
## Où se trouve « Mon équipe » ?
- [x] Dans le menu à votre nom
- [ ] Dans ⚙ Admin → Comptes
- [ ] Dans Training → Mon plan
## Un employé signe son Début d'année. Que se passe-t-il pour son gestionnaire ?
- [x] Il reçoit un message pour approuver le plan annuel
- [ ] Rien jusqu'à la Mi-année
- [ ] Il reçoit un courriel de rappel chaque semaine
## Que contiennent les messages de signature ?
- [x] Seulement l'étape et un lien, aucun texte privé
- [ ] Le texte complet des commentaires
- [ ] Le profil de l'employé
## Le gestionnaire rouvre une étape. Que se passe-t-il ?
- [x] L'employé est prévenu ; les étapes suivantes se rouvrent
- [ ] Rien n'est envoyé ; seule cette étape se rouvre
- [ ] L'employé est prévenu ; seule cette étape se rouvre
## Depuis « Mon équipe », comment ouvrir le plan de formation d'une personne ?
- [x] Bouton « Plan de formation » de sa carte
- [ ] Il faut passer par ⚙ Admin
- [ ] Ce n'est pas possible
## Qui voit l'écran « Mon équipe » d'un gestionnaire ?
- [x] Ce gestionnaire seulement
- [ ] Toute son équipe
- [ ] Tous les administrateurs
"""
