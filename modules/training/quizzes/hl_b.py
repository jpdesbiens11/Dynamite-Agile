"""Quizzes HL-06 to HL-10 (0.50.10, D-B-128): medium difficulty, every answer in the Help chapter of the topic
(and the FAQ for the CSV round trip)."""

HL_06 = """# Quiz : Agile — exécuter
pass: 80
## Vous créez un ticket sans choisir de responsable. Qui en devient responsable ?
- [x] Vous, le créateur
- [ ] Personne : il reste « non assigné »
- [ ] L'Admin du Space
## À quoi sert le Backlog ?
- [x] Ordonner le travail, préparer un sprint, puis le démarrer
- [ ] Ranger les tickets fermés des sprints précédents
- [ ] Planifier les phases du projet sur plusieurs mois
## Sur le Board, qui déplace une carte d'une colonne à l'autre ?
- [ ] N'importe quel membre du Space
- [x] Son responsable, selon le workflow du Space
- [ ] Le Scrum Master seulement
## Dans un ticket, comment pose-t-on une question au client ?
- [ ] En créant un ticket de type « Question »
- [x] En cochant « Question » sur un commentaire
- [ ] En écrivant @client dans la description
## Quels liens un ticket peut-il porter ?
- [x] « bloque »
- [x] « implémente » (vers un requirement Goldmine)
- [ ] « facture »
## Où un administrateur règle-t-il workflows, types, labels et versions d'un Space ?
- [x] ⚙ Admin → Paramètres du Space
- [ ] Menu à votre nom → Paramètres
- [ ] Dans chaque ticket
## Quelle est la règle d'or de l'aller-retour CSV des tickets ?
- [ ] Repartir d'un fichier vide à chaque fois
- [x] Partir toujours d'un export récent, modifier, réimporter
- [ ] Ne jamais réimporter un fichier déjà importé
## Vous réimportez exactement le même fichier une deuxième fois. Que se passe-t-il ?
- [x] Rien ne change : les lignes sont « inchangée »
- [ ] Tous les tickets sont dupliqués
- [ ] L'import est refusé en entier
## Une ligne de votre CSV est refusée. Qu'affiche la plateforme ?
- [x] Son numéro de ligne Excel et le correctif ; rien n'est écrit pour elle
- [ ] Un message « fichier invalide » ; rien n'est écrit pour tout le fichier
- [ ] Rien : la ligne est ignorée en silence, les autres sont écrites
## Un collègue a modifié un ticket entre votre export et votre import. Que se passe-t-il ?
- [ ] Votre version écrase la sienne, et il reçoit un message
- [x] La ligne est refusée en nommant les champs en conflit
- [ ] La valeur la plus récente des deux est gardée, champ par champ
## Que permet l'import CSV des questions client ?
- [ ] Créer et supprimer des questions
- [x] Ajouter des réponses seulement
- [ ] Changer le responsable des tickets
## Où trouve-t-on la méthode Agile pas à pas, avec captures ?
- [x] Dans la Base de connaissances du Space HEADLAMP (Dynamite)
- [ ] Dans le Space wiki TOOLS, avec les méthodes de conception
- [ ] Dans Help → FAQ, question « Agile, Goldmine, Exploration »
## Quelle question Agile aide-t-il à répondre ?
- [ ] Que doit faire le produit ?
- [ ] Quand, dans les grandes lignes ?
- [x] Qui fait quoi, maintenant ?
## Vous n'êtes pas responsable d'un ticket et vous voulez prévenir un collègue. Que faites-vous ?
- [x] Un commentaire avec @collègue
- [ ] Vous modifiez la description pour l'ajouter
- [ ] Vous changez le status du ticket
## Qu'est-ce que « Tickets » dans le panneau de gauche ?
- [x] La liste filtrable de tous les tickets du Space
- [ ] Le Board du sprint actif
- [ ] La liste des tickets fermés seulement
"""

HL_07 = """# Quiz : Change Management — PR, bugs, ECN
pass: 80
## Où ouvre-t-on un problème (PR) ou un bug logiciel ?
- [ ] Dans Goldmine → Q&A, comme question à l'équipe
- [x] Dans Agile → « Change Management »
- [ ] Dans la Liste Audit, comme observation
## Que comprend l'analyse d'un PR ?
- [x] La sévérité
- [x] Le confinement
- [x] La cause racine
- [ ] Le choix du fournisseur de remplacement
## Que décrit un ECN ?
- [x] La classe et la raison du changement
- [x] Les impacts forme-ajustement-fonction, certification et sécurité
- [x] Ses Affected Items
- [ ] Les heures déclarées sur le changement
## Qu'est-ce qu'un Affected Item ?
- [x] Un article touché, de sa révision actuelle à la nouvelle
- [ ] Un collègue dont le travail est touché, à prévenir
- [ ] Un test de la Test Base à refaire après le changement
## « Submit to CCB » est bloqué. Pourquoi, le plus souvent ?
- [x] Il manque au moins un Affected Item ; le message dit ce qui manque
- [ ] Le CCB ne siège que le lundi
- [ ] Un ECN ne se soumet qu'à partir de Goldmine
## Qui approuve ou rejette un ECN soumis au CCB ?
- [x] Un administrateur du Space, parmi les approbateurs nommés
- [ ] Son auteur, une fois l'analyse terminée
- [ ] Le responsable du PR d'origine
## Que faut-il avant la fermeture d'un ECN approuvé ?
- [x] L'implantation, puis la vérification (sub-tasks terminées)
- [ ] Rien : l'approbation du CCB le ferme d'elle-même
- [ ] Une deuxième approbation du CCB, après l'implantation
## Dans quel ordre se suivent les étapes ?
- [x] PR → analyse → ECN → CCB → implantation → vérification → fermeture
- [ ] PR → ECN → analyse → implantation → CCB → vérification → fermeture
- [ ] PR → CCB → analyse → ECN → vérification → implantation → fermeture
## Une étape est bloquée. Comment savez-vous quoi faire ?
- [x] L'étape affiche ce qui manque (ex. « au moins un Affected Item »)
- [ ] Il faut lire le Journal d'audit
- [ ] Il faut demander à un administrateur de débloquer
## Dans la méthode GTD de la BDC, que représente un ECN en « CCB Review » ?
- [ ] Une Next Action
- [x] Un « Waiting For »
- [ ] Un élément « Someday / Maybe »
> Vous attendez la décision des autres.
## Peut-on sortir les changements (PR, ECN) dans Excel ?
- [x] Oui, en CSV par Agile → Import / Export (sortie seulement)
- [ ] Oui, et les réimporter pour les modifier en masse
- [ ] Non, jamais
## « Forme-ajustement-fonction » d'un ECN, c'est…
- [x] L'impact sur la forme, l'interchangeabilité (fit) et la fonction de l'article
- [ ] Le format, la mise en page et le gabarit du document ECN
- [ ] L'impact sur le coût, le délai et la quantité à commander
"""

HL_08 = """# Quiz : Tools — Design et Generator
pass: 80
## Où sont la page et la FAQ de chaque méthode de Design ?
- [ ] Dans Help → FAQ
- [x] Dans le Space wiki TOOLS
- [ ] Dans Goldmine
## Que donne Generator pour un document ?
- [x] Un numéro unique
- [x] Le nom de fichier complet
- [x] Le dossier où l'enregistrer
- [ ] Le texte du document
## Qui attribue le numéro final d'une référence Generator ?
- [ ] Votre navigateur, à l'heure de votre poste, dès l'aperçu
- [x] Le serveur, au moment de « Réserver la référence »
- [ ] L'Admin du Space, qui valide les demandes du jour
## Une référence n'est plus utile. Que faire ?
- [x] L'annuler : elle reste au registre
- [ ] La supprimer du registre pour libérer le numéro
- [ ] La réattribuer à un autre document du même type
## Le numéro Generator ne correspond pas à l'heure de votre montre. Pourquoi ?
- [x] C'est une date-heure série Excel en UTC
- [ ] Le serveur n'est pas à l'heure de Montréal
- [ ] Le numéro est un compteur, pas une heure
> En été, la partie date change à 20 h, heure de Montréal.
## Que faire avec « Copier le nom » ?
- [x] Le coller dans le Nom de fichier de Word (Enregistrer sous)
- [ ] Le coller dans le titre de la page Dynamite du document
- [ ] Le coller dans le champ Source Doc d'un requirement
## Comment se déroule le brainwriting dans l'outil Idéation ?
- [x] En paires qui changent à chaque tour ; on voit en direct ce qu'écrit son partenaire
- [ ] Chacun seul, sans voir les idées des autres jusqu'à la fin
- [ ] Oralement, l'animateur note les idées
## Sur quoi sont rangés les types de documents de Generator ?
- [x] Les phases du PDP : pré-étude, étude conceptuelle, conception, fabrication et validation
- [ ] Les chapitres d'une norme
- [ ] L'ordre alphabétique seulement
## À quelle étape du PDP range-t-on un CdCF dans Generator ?
- [x] 11 — Définition des spécifications d'ingénierie
- [ ] 01 — Étude de marché
- [ ] 21 — Tests de validation
## Quel livrable termine l'étude conceptuelle ?
- [x] Le RCS (rapport de conception système)
- [ ] Le MIP
- [ ] Le RVE
"""

HL_09 = """# Quiz : Timesheet — déclarer ses heures
pass: 80
## Que faut-il pour pouvoir soumettre la semaine ?
- [ ] Au moins 40 h
- [x] Une courte description sur chaque plage
- [ ] L'accord préalable de l'administrateur
> Une plage sans description bloque la soumission (ligne en rouge).
## Qui approuve votre semaine ?
- [x] Votre gestionnaire, choisi dans le menu à votre nom → Paramètres
- [x] Un administrateur
- [ ] N'importe quel collègue
## Les heures se saisissent par…
- [ ] Minute
- [x] Quart d'heure
- [ ] Demi-heure
## Une semaine « Returned » signifie…
- [ ] Elle est approuvée et renvoyée pour archive
- [x] Elle doit être corrigée puis soumise de nouveau
- [ ] Elle est revenue en brouillon parce qu'elle était vide
> La note du gestionnaire explique quoi corriger.
## Vous avez soumis trop vite. La semaine n'est pas encore approuvée. Que faire ?
- [x] « Retirer la soumission »
- [ ] Attendre que le gestionnaire la renvoie
- [ ] Ajouter une plage négative pour corriger
## Vous voulez recopier toutes les plages de lundi sur le reste de la semaine. Quel bouton ?
- [x] « ⧉ Copier la journée », puis « Lundi à vendredi »
- [ ] « ⧉ » au bout d'une ligne
- [ ] « Copier une semaine passée… »
> « ⧉ » au bout d'une ligne ne copie que cette plage.
## Une copie ferait dépasser 24 h dans une journée. Que se passe-t-il ?
- [ ] Les heures en trop sont reportées au lendemain
- [x] La copie est refusée
- [ ] La journée passe en rouge mais la copie est faite
## Une semaine approuvée doit être corrigée. Que faire ?
- [ ] « Retirer la soumission », puis la corriger
- [x] Demander à un administrateur de la rouvrir
- [ ] La corriger la semaine suivante avec une plage négative
## « Copier une semaine passée… » permet de…
- [x] Reprendre une semaine précédente, jour pour jour
- [ ] Reprendre la semaine d'un collègue de la même équipe
- [ ] Reprendre la moyenne des quatre dernières semaines
## La Recherche de la barre du haut trouve-t-elle vos feuilles de temps ?
- [ ] Oui, comme tout le reste, par la description des plages
- [x] Non : elles sont privées et ne sont pas couvertes
- [ ] Seulement par la Recherche avancée, type « Timesheet »
## Qu'offre « ⚙ Admin → Export et rapport Word » aux administrateurs ?
- [x] Un classeur Excel ou un rapport Word avec attestation à signer
- [ ] L'approbation en lot de toutes les semaines soumises
- [ ] Un export CSV par employé à réimporter après correction
"""

HL_10 = """# Quiz : Recherche, palette et Audit
pass: 80
## Vous cherchez « élément chauffant buse ». Quels résultats sortent ?
- [ ] Ceux qui contiennent au moins un des trois mots
- [x] Ceux qui contiennent les trois mots
- [ ] Ceux qui contiennent la phrase exacte
> Tous les mots doivent apparaître ; « phrase exacte » entre guillemets.
## Vous tapez « etancheite ». Trouvez-vous « Étanchéité » ?
- [x] Oui : accents et majuscules sont ignorés
- [ ] Non : il faut l'accent
- [ ] Seulement dans les titres
## Comment exclure un mot de la recherche ?
- [ ] NOT mot
- [x] -mot
- [ ] !mot
## Que permet « ⚙ Recherche avancée » ?
- [x] Choisir les Spaces et les types de résultats
- [x] Titres seulement, dates, éléments ouverts seulement
- [ ] Chercher dans les feuilles de temps des collègues
## Quand utiliser la palette (Ctrl+K) plutôt que la Recherche ?
- [x] Pour aller quelque part (onglet, Space, écran d'Admin)
- [ ] Pour trouver une phrase dans une page
- [ ] Pour filtrer sur vos éléments
## Dans la palette, comment choisir et fermer ?
- [x] ↑ ↓ puis Entrée ; Échap pour fermer
- [ ] Clic droit puis « Ouvrir »
- [ ] Tab puis Espace
## Pendant la frappe, la Recherche montre les meilleurs résultats. Et Entrée ?
- [x] Ouvre la page complète des résultats
- [ ] Ouvre le premier résultat
- [ ] Efface la recherche
## Vous voyez un problème à l'écran. Que faire ?
- [x] Cliquer « Audit » sur cet écran, décrire le problème, envoyer
- [ ] Écrire un ticket dans le Space HEADLAMP
- [ ] Envoyer un courriel à l'IT
## Audit ne capture pas la page automatiquement. Pourquoi, et que faire ?
- [x] Elle demande HTTPS : prenez la capture (Win+Maj+S) et collez-la
- [ ] Votre compte n'a pas le droit Audit : demandez-le
- [ ] La page est trop longue : envoyez sans capture
## Que compte le chiffre du bouton « Liste Audit » ?
- [ ] Vos observations envoyées
- [x] Les observations ouvertes
- [ ] Les observations de la semaine
## Que montre la vue « Plan de révisions » de la Liste Audit ?
- [x] Une colonne par révision cible
- [ ] Les révisions des pages Dynamite
- [ ] Les Affected Items des ECN
## Qui planifie une observation dans une révision ?
- [x] Un administrateur
- [ ] Son auteur
- [ ] Tout Éditeur
## La Recherche ne trouve pas votre texte. Quel est le premier réflexe ?
- [x] Essayer moins de mots, ou un mot plus court (2 lettres minimum)
- [ ] Ajouter des mots pour préciser
- [ ] Demander à un administrateur de réindexer
> Tous les mots doivent apparaître : plus il y en a, moins il y a de résultats.
## Qui peut lire la Liste Audit ?
- [x] Tout le monde
- [ ] Les administrateurs seulement
- [ ] L'auteur de chaque observation seulement
## Que cherche la Recherche, entre autres ?
- [x] Pages et commentaires, tickets, requirements, needs, tests
- [x] PR / ECN, questions client, références Generator, personnes
- [ ] Les heures de chaque collègue
"""
