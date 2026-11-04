"""Quizzes HL-11 to HL-14 (0.50.10, D-B-128): medium difficulty, every answer in the Help chapter of the topic
(and the FAQ for backups and confidentiality)."""

HL_11 = """# Quiz : Admin (administrateurs)
pass: 80
## Quels sont les trois groupes de l'onglet ⚙ Admin ?
- [x] Comptes, Spaces, Plateforme
- [ ] Utilisateurs, Modules, Réseau
- [ ] Lecture, Écriture, Administration
## « Dupliquer… » sur un compte sert à…
- [x] Créer un compte avec les mêmes droits qu'un profil existant
- [ ] Copier les pages Dynamite d'un utilisateur
- [ ] Fusionner deux comptes
## Dans quel ordre supprime-t-on un Space ?
- [x] Archiver → sauvegarder → supprimer, en confirmant par la clé du Space
- [ ] Supprimer directement, puis archiver la sauvegarde
- [ ] Retirer tous les membres : le Space disparaît seul
> Une sauvegarde complète est créée juste avant la suppression.
## Que sont les « 2 × 3 chances » de ↺ Restaurer ?
- [x] 3 versions du code et 3 points de restauration des données
- [ ] 2 sauvegardes par jour, chacune gardée 3 jours
- [ ] 3 sauvegardes .zip par Space, sur 2 serveurs
## Quand un point de restauration des données est-il pris automatiquement ?
- [x] Avant chaque mise à jour, import ou configuration
- [x] Une fois par jour
- [ ] À chaque enregistrement d'une page
## Une erreur a abîmé un seul Space. Que faire ?
- [x] « Récupérer un Space… », qui le ramène dans un nouveau Space
- [ ] « Revenir à ce point… », qui ne touche que ce Space
- [ ] « Revenir à la v… », la version précédente du code
## Que se passe-t-il avec « Revenir à ce point… » ?
- [x] Tout le site revient à ce moment ; un point « avant retour » est pris d'abord
- [x] Le journal d'audit est gardé et tout le monde se reconnecte
- [ ] Seul votre compte revient en arrière
## Une sauvegarde .zip d'un Space se restaure…
- [ ] Toujours par-dessus le Space d'origine
- [x] Toujours dans un nouveau Space
- [ ] Seulement par l'IT
## Que contient le volet « Framework » de Update et sauvegardes ?
- [x] Exporter le code pour Claude, puis vérifier et appliquer le zip rendu
- [ ] Exporter les comptes et les Spaces en paquets scellés
- [ ] Déménager tout le site vers un nouveau serveur
## Le volet « Configuration » garde…
- [x] Les réglages en .md, avec leurs versions sur 3 mois
- [ ] Les certificats TLS et leur date d'expiration
- [ ] Les 3 dernières versions du code du site
## Que montre Admin → Sécurité réseau ?
- [x] Ce qui protège l'échange navigateur ↔ serveur (TLS 1.3, certificat, mTLS, HSTS)
- [ ] Les comptes aux mots de passe faibles et leurs dernières connexions
- [ ] Les adresses IP bloquées par le pare-feu Windows de chaque poste
## Admin → Confidentialité peut-il empêcher complètement les captures d'écran ?
- [x] Non : il dissuade et journalise ; le vrai blocage relève des postes
- [ ] Oui : le blocage de l'impression bloque aussi Impr. écran
- [ ] Oui, si le flou hors focus et le filigrane sont activés ensemble
> Filigrane nominatif, blocages, flou hors focus : une capture désigne sa source.
## Pour partager le serveur de développement avec un collègue, quel fichier lui envoyer ?
- [x] data/tls/ca.crt, à installer une fois sur son poste
- [ ] data/tls/server.key, pour qu'il ouvre la connexion
- [ ] Lancer_dev_reseau.bat, à lancer sur son poste
## En partage de développement, où le compte admin / admin s'ouvre-t-il ?
- [x] Seulement sur le poste qui fait tourner la plateforme
- [ ] Sur tous les postes du réseau privé
- [ ] Nulle part : il est désactivé
## Le collègue ne voit rien en partage de développement. Cause la plus probable ?
- [x] Le pare-feu Windows bloque Python : la règle se demande à l'IT
- [ ] Il faut redémarrer le serveur en production
- [ ] Le collègue doit avoir le rôle Administrateur
"""

HL_12 = """# Quiz : Dashboard et Messages (@mentions)
pass: 80
## Qu'affiche le Dashboard ?
- [x] Ce qui vous attend dans tous vos Spaces
- [ ] Ce qui vous attend dans votre Space par défaut
- [ ] L'activité récente de toute l'équipe
## Vous changez un status depuis le Dashboard (menu ▾). Quelles étapes sont proposées ?
- [ ] Toutes les étapes du workflow du Space
- [x] Les étapes permises depuis l'étape actuelle
- [ ] Seulement l'étape suivante, puis « Done »
## Que fait le bouton « Mes éléments » de la barre du haut ?
- [x] Partout, n'affiche plus que vos éléments
- [ ] Ouvre la liste de vos éléments dans un nouvel écran
- [ ] Filtre le Dashboard seulement
## Où pouvez-vous mentionner un collègue avec @ ?
- [x] Dans une page Dynamite ou un commentaire
- [x] Dans un ticket ou un requirement
- [ ] Dans une plage de Timesheet
## Où la personne mentionnée reçoit-elle votre message ?
- [ ] Par courriel, avec le lien
- [x] Dashboard → Messages → Reçus
- [ ] Dans les commentaires de la page seulement
## Où voyez-vous si votre message a été lu ?
- [x] Messages → Envoyés
- [ ] Messages → Reçus
- [ ] Messages → Traités
## Vous cliquez « Répondre ici » sous un message reçu. Où va la réponse ?
- [x] En commentaire à l'endroit d'origine, signée par vous
- [ ] Dans les Messages du demandeur seulement, sans trace ailleurs
- [ ] Dans une note @moi de votre Dashboard
> Le message passe dans « Traités ».
## Que fait le demandeur avec « Acknowledge » ?
- [x] Il retire la Réponse de son Dashboard
- [ ] Il rouvre la question
- [ ] Il approuve votre ticket
## Que fait « @votre-identifiant » ?
- [x] Dépose une Note pour vous-même dans vos Messages (badge « Moi »)
- [ ] Envoie un message à tous les membres du Space
- [ ] Rien : on ne peut pas se mentionner
## Vous mentionnez un collègue qui n'a pas accès au Space. Que se passe-t-il ?
- [x] Il n'est pas prévenu, et l'enregistrement vous le dit
- [ ] Il reçoit l'accès Lecteur au Space automatiquement
- [ ] L'enregistrement de la page est refusé
## Que compte la pastille du Dashboard ?
- [x] Les messages non lus
- [ ] Les tickets en retard
- [ ] Les semaines à soumettre
## Un administrateur utilise « Voir le tableau de bord de » un employé. Que voit-il ?
- [x] Sa charge en lecture seule ; ses Messages restent privés
- [ ] Sa charge et ses Messages, en lecture seule
- [ ] Sa charge, qu'il peut aussi modifier à sa place
## Vous cliquez sur un compteur en haut du Dashboard. Que se passe-t-il ?
- [x] La page descend à sa section
- [ ] La liste complète s'ouvre dans un autre onglet
- [ ] Le compteur se remet à zéro
"""

HL_13 = """# Quiz : Testing — tests, procédures et Test Plans
pass: 80
## Comment fonctionne « une Test Base par Space » ?
- [x] Chaque Space reçoit une copie de la base TESTING, modifiable sans toucher les autres
- [ ] Tous les Spaces lisent la base TESTING ; seul TESTING la modifie
- [ ] Chaque Space crée sa Test Base à partir de rien, par import CSV
## Qu'est-ce qui reste commun à tous les Spaces dans Testing ?
- [x] Les listes centrales
- [x] Les procédures (wiki TESTING)
- [ ] Les tests de chaque Test Base
## Quelles sont les categories d'un test ?
- [x] Standard, Industry Practice, Custom Test
- [ ] Mandatory, Optional, Deprecated
- [ ] Qualification, Acceptance, Production
## Vous créez un « Nouveau Test » dans le sujet Custom. Comment démarre-t-il ?
- [x] Avec un identifiant qui suit le sujet, en Draft
- [ ] Avec un numéro libre que vous choisissez, déjà actif
- [ ] Sans identifiant jusqu'à son approbation par TESTING
## Quel est le cycle d'un Test Plan fournisseur ?
- [x] Draft → Sent to Supplier → Results Received → Closed
- [ ] Draft → Approved → Sent to Supplier → Closed
- [ ] Draft → Sent to Supplier → Approved → Results Received
## Que faut-il pour passer un Test Plan à « Results Received » ?
- [ ] La signature électronique du fournisseur
- [x] Joindre les résultats en PDF
- [ ] Le Word du plan, signé et rendu
## Où choisit-on le fournisseur d'un Test Plan ?
- [x] Dans la liste centrale Test Location
- [ ] En texte libre
- [ ] Dans Admin → Utilisateurs
## Il manque un équipement dans la liste Test Equipment. Que faire ?
- [ ] L'écrire en texte libre dans le champ du test
- [x] Demander l'ajout à un Admin du Space TESTING
- [ ] L'ajouter vous-même dans la copie de votre Space
## Une entrée de liste centrale est remplacée. Que devient l'ancienne ?
- [x] Elle reste sur ses tests, mais n'est plus proposée
- [ ] Elle est effacée, et remplacée sur tous les tests
- [ ] Elle est remplacée par la nouvelle sur tous les tests
## Comment se passe l'import CSV de tests ?
- [x] Un aperçu s'affiche avant d'écrire
- [ ] Les tests sont écrits tout de suite
- [ ] L'import n'existe pas
"""

HL_14 = """# Quiz : Training — votre plan de formation
pass: 80
## Dans quel ordre un item du plan avance-t-il ?
- [x] To Do → In Progress → Completed → Achieved
- [ ] To Do → Completed → In Progress → Achieved
- [ ] In Progress → Achieved → Completed
## Qui corrige le test ?
- [ ] Votre navigateur, dès que vous cochez
- [x] Le serveur, après la remise
- [ ] Votre gestionnaire, depuis votre plan
> Les réponses ne sont jamais envoyées au navigateur avant la correction.
## Vous obtenez 67 % à un test dont le seuil est 80 %. Que se passe-t-il ?
- [ ] Vous repassez tout le test, avec de nouvelles questions
- [x] Les questions manquées reviennent jusqu'à être réussies
- [ ] Votre gestionnaire doit rouvrir le test
## Pendant une reprise des questions manquées, que voyez-vous ?
- [x] Seulement les questions manquées, avec les réponses dans un autre ordre
- [ ] Toutes les questions avec les bonnes réponses cochées
- [ ] Les explications de chaque question manquée avant de répondre
## Que devient l'item quand le test est réussi (directement ou après les reprises) ?
- [x] Il passe à « Completed », en vert
- [ ] Il passe à « Achieved »
- [ ] Il reste « In Progress » jusqu'au clic « Marquer complété »
## Qui passe un item à « Achieved » ?
- [ ] L'employé, dès que le test est réussi
- [x] Le gestionnaire, après le test réussi et son évaluation
- [ ] Un Admin du Space TRAINING, en fin d'année
## Qui est votre gestionnaire pour Training ?
- [x] La personne choisie dans menu à votre nom → Paramètres
- [ ] L'Admin du Space TRAINING
- [ ] Le premier administrateur de la liste
## Que garde votre gestionnaire après une réussite par reprises ?
- [x] La note du test complet, visible sur l'item
- [ ] 100 %, puisque toutes les questions sont réussies
- [ ] La note de la dernière reprise
## Où l'évaluation de l'année reprend-elle les topics du plan de formation ?
- [x] Dans « Mes objectifs »
- [ ] Dans « Mon équipe » seulement
- [ ] Dans le profil professionnel
## Qui gère les topics et leurs tests ?
- [x] Les administrateurs et les Admin du Space TRAINING
- [ ] Chaque gestionnaire, pour son équipe
- [ ] Tout Éditeur du Space TRAINING
## Votre gestionnaire peut-il passer le test à votre place ?
- [x] Non
- [ ] Oui, depuis « Plan · <nom> »
- [ ] Oui, s'il est administrateur
## Quel item pouvez-vous retirer vous-même de votre plan ?
- [x] Un item « To Do »
- [ ] Un item « Completed »
- [ ] N'importe quel item
## Avec 15 questions et un seuil de 80 %, combien d'erreurs au plus au test complet pour réussir directement ?
- [ ] 2
- [x] 3
- [ ] 4
> 12 / 15 = 80 % : 3 erreurs passent, 4 donnent 73 % et une reprise.
## Que règle l'écran « Workflow » de Training ?
- [x] Quel rôle peut faire chaque passage de status
- [ ] L'ordre des topics dans les plans
- [ ] Le seuil de réussite de chaque test
## Les topics HL-01 à HL-14 correspondent à…
- [x] Une étape chacune du guide Help
- [ ] Les 14 Spaces de la plateforme
- [ ] Les 14 onglets de la barre du haut
"""
