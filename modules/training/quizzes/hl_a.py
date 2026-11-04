"""Quizzes HL-01 to HL-05 (0.50.10, D-B-128): medium difficulty, every answer in the Help chapter of the topic."""

HL_01 = """# Quiz : Bienvenue, barre du haut et réglages
pass: 80
## Vous n'avez pas encore donné votre clé de traçabilité de 3 lettres. Que se passe-t-il ?
- [ ] Vous pouvez écrire, mais vos modifications sont signées « ??? »
- [x] Aucune écriture n'est acceptée : un bandeau jaune « Initiales requises » s'affiche
- [ ] Seul Dynamite est bloqué ; les autres outils fonctionnent
> Sans initiales, le serveur refuse toute écriture : elles signent chaque modification.
## Où donne-t-on ses initiales ?
- [ ] Admin → Utilisateurs
- [x] Menu à votre nom → Paramètres → « Mes initiales »
- [ ] Sur l'Accueil, dans « Qui contacter ? »
## Quelle est la longueur minimale du mot de passe choisi à la première connexion ?
- [ ] 8 caractères
- [x] 12 caractères
- [ ] 16 caractères
## À quoi sert surtout la palette Ctrl+K ?
- [x] Aller vite quelque part : un onglet, un Space, un écran d'Admin
- [ ] Chercher un mot dans le contenu de toutes les pages
- [ ] Enregistrer la page en cours
> Pour retrouver un contenu, c'est la Recherche de la barre du haut ; la palette sert à naviguer.
## Que signifie le badge [new] à côté d'un champ ou d'un bouton ?
- [ ] Le champ est obligatoire
- [x] C'est une nouveauté de la dernière version ; le badge disparaît quand vous l'avez utilisée
- [ ] Le champ a été modifié par un collègue depuis votre dernière visite
## Vous cochez un Space dans la marge gauche de la page d'ouverture d'Agile. Quel est l'effet ?
- [x] Il devient votre Space par défaut : chaque onglet s'ouvre directement sur lui
- [ ] Il devient le Space de tous les membres de l'équipe
- [ ] Il est ajouté à vos favoris de la palette seulement
> « ↺ Réinitialiser le Space par défaut », en bas de la liste, ramène à la liste des Spaces.
## Comment masquer le panneau de gauche d'un outil ?
- [ ] Double-cliquer sur le titre de l'outil
- [x] Bouton bleu « <<< » (« >>> » pour le rouvrir), ou glisser son bord pour le redimensionner
- [ ] Il ne se masque pas ; seul un administrateur peut le retirer
## Qu'est-ce que le Space HeadLamp [Sandbox] ?
- [ ] Le Space où l'on déclare les heures de formation
- [x] Un bac à sable pour tout essayer : rien n'y touche aux vrais Spaces
- [ ] Le Space des administrateurs pour tester les mises à jour
## Vous avez oublié votre mot de passe. Que faire ?
- [ ] Le bouton « Mot de passe oublié » envoie un courriel
- [x] Un administrateur vous donne un mot de passe temporaire (Admin → Utilisateurs)
- [ ] Recréer un compte avec le même identifiant
## La plateforme est en français. Quels mots restent en anglais ?
- [x] Les termes techniques (status, workflow, Test Plan…)
- [ ] Les boutons et les messages d'erreur, pour rester proches des standards
- [ ] Aucun : tout est traduit, avec un lexique EN → FR dans la BDC
> Pour une autre langue que le français, « Traduire » du navigateur.
## Combien d'étapes signées compte l'évaluation de l'année dans « Mes objectifs » ?
- [ ] 2 : mi-année et fin d'année
- [x] 3 : Début d'année, Mi-année, Fin d'année
- [ ] 4 : une par trimestre
## Où voit-on qui s'occupe de quoi dans l'entreprise ?
- [x] Sur l'Accueil, dans « Qui contacter ? »
- [ ] Dans Admin → Journal d'audit
- [ ] Dans Timesheet → Spaces et organismes
"""

HL_02 = """# Quiz : Spaces, rôles et droits
pass: 80
## Comment vos droits sont-ils donnés sur la plateforme ?
- [ ] Une fois pour tous les Spaces, selon votre équipe dans l'annuaire
- [x] Space par Space, plus un rôle Administrateur global
- [ ] Outil par outil : un droit Agile, un droit Dynamite, un droit Goldmine…
## Que peut faire un Lecteur dans un Space ?
- [x] Tout lire
- [x] Commenter et poser des questions
- [x] Exporter
- [ ] Créer des requirements
> Créer et modifier pages, tickets et requirements demande le rôle Éditeur.
## Que peut faire un Admin du Space, en plus d'un Éditeur ?
- [ ] Créer de nouveaux Spaces
- [x] Gérer les membres de ce Space (menu à votre nom → « Membres de mes Spaces »)
- [ ] Approuver les feuilles de temps de tout le monde
## Qui peut créer un Space ou un compte ?
- [ ] Tout Éditeur
- [ ] L'Admin du Space concerné
- [x] Un administrateur
## Qui peut modifier un ticket Agile ?
- [ ] Tout Éditeur du Space, puisqu'il peut créer des tickets
- [x] Son responsable (l'assigné), ou un administrateur
- [ ] Son créateur, même après avoir changé l'assigné
## Un ticket n'a pas de responsable. Comment le prendre ?
- [x] Bouton « Prendre le ticket »
- [ ] Demander à un administrateur de vous l'assigner : c'est la seule façon
- [ ] Le modifier : vous en devenez responsable automatiquement
## Vous voulez confier votre ticket à un collègue. Que faites-vous ?
- [x] En tant que responsable, vous changez l'assigné
- [ ] Le collègue clique « Prendre le ticket »
- [ ] Vous le supprimez et il le recrée
> « Prendre le ticket » ne sert qu'aux tickets sans responsable.
## Où voyez-vous votre rôle dans chacun de vos Spaces ?
- [x] Sur l'Accueil
- [ ] Dans le Journal d'audit
- [ ] Dans chaque page Dynamite, en bas
## Un Space qui vous manque ? Que faire ?
- [ ] Le créer vous-même avec la même clé
- [x] Demander l'accès à un administrateur
- [ ] Le chercher avec Ctrl+K : il s'ouvre même sans droit
## Lecteur d'un Space, vous voulez faire une remarque sur un ticket d'un collègue. Que pouvez-vous faire ?
- [x] Le commenter
- [ ] Modifier sa description
- [ ] Changer son status
## Où un administrateur donne-t-il les droits de plusieurs comptes d'un coup, en texte ?
- [ ] Admin → Journal d'audit, en rejouant une ligne
- [x] Admin → Règles d'accès, vérifiées à blanc avant d'appliquer
- [ ] Admin → Setup des Spaces, onglet Membres
## Que montre la grille Admin → Droits ?
- [x] Les comptes × les Spaces, avec le rôle dans chaque case
- [ ] Les écrans × les boutons permis pour chaque rôle
- [ ] Les comptes × les outils, avec un droit oui / non par outil
"""

HL_03 = """# Quiz : Dynamite — documenter
pass: 80
## Qu'est-ce qui est créé avec chaque nouveau Space, dans Dynamite ?
- [x] Une page d'accueil (objet, équipe, jalons, accès rapides)
- [ ] Une page vide sans titre
- [ ] Rien : le wiki se crée à la première page
## Dans l'éditeur visuel, quelle touche ouvre le menu des blocs ?
- [ ] « # »
- [x] « / »
- [ ] « @ »
> « @ » sert aux mentions de collègues.
## Que se passe-t-il à chaque enregistrement (Ctrl+S) d'une page ?
- [ ] La version précédente est écrasée
- [x] Une version est créée ; « Historique » compare et restaure
- [ ] La page est envoyée aux membres par courriel
## Où discute-t-on d'une page sans toucher à son texte ?
- [x] Dans les commentaires sous la page
- [ ] Dans un panneau « note » au milieu du texte
- [ ] Dans le mode Source
## Quels panneaux colorés peut-on insérer ?
- [x] Info
- [x] Note
- [x] Avertissement
- [x] Succès
- [ ] Vidéo intégrée
## Vous enregistrez une page qu'un collègue vient de modifier pendant que vous éditiez. Que se passe-t-il ?
- [ ] Votre version est enregistrée ; la sienne reste dans l'Historique
- [ ] Les deux versions sont fusionnées, paragraphe par paragraphe
- [x] L'enregistrement est refusé avec le nom de l'auteur
> Copiez votre texte, rechargez la page, puis réappliquez vos modifications.
## Quels formats « ✨ Importer d'une IA » accepte-t-il ?
- [x] Markdown
- [x] HTML
- [x] Texte
- [ ] Un fichier PDF
## Après le collage dans « Importer d'une IA », que faites-vous ?
- [x] Vérifier l'aperçu, puis insérer au curseur ou remplacer la page
- [ ] Rien : la page est remplacée dès le collage
- [ ] Envoyer l'aperçu à un administrateur pour approbation
## Vous voulez une page Dynamite en PDF. Que faut-il ?
- [ ] Rien : tout le monde peut exporter
- [x] Le droit d'export, donné compte par compte
- [ ] Le rôle Admin du Space
> Export PDF / Word d'une page ou de toute sa branche.
## Une page et ses sous-pages doivent passer dans un autre Space. Que faire ?
- [x] « Déplacer / Copier » la page : ses sous-pages suivent
- [ ] Exporter la branche en Word puis l'importer dans l'autre Space
- [ ] « Copier / composer un Space », réservé aux administrateurs
## Où se trouve la Base de connaissances (BDC) ?
- [x] Dans HEADLAMP → Dynamite
- [ ] Dans Testing → Listes
- [ ] Dans Help → FAQ
## Vous réenregistrez une page qui contenait déjà « @ana ». Ana reçoit-elle un nouveau message ?
- [ ] Oui, à chaque enregistrement, pour rappel
- [x] Non : seules les mentions ajoutées par la nouvelle version partent
- [ ] Oui, si plus de 24 h se sont écoulées depuis le premier message
## Le mode Source de l'éditeur sert à…
- [x] Écrire avec une syntaxe courte au lieu de la barre d'outils
- [ ] Voir le HTML de la page pour le modifier
- [ ] Comparer deux versions
"""

HL_04 = """# Quiz : Goldmine — needs et requirements
pass: 80
## Que veut dire IADT pour la Verification Method ?
- [x] Inspection, Analysis, Demonstration, Test
- [ ] Integration, Acceptance, Design, Traceability
- [ ] Inspection, Audit, Design Review, Test
## Un requirement est vérifié par analyse, sans essai. Quelle Test Procedure choisir ?
- [ ] Aucune : la Verification Method « Analysis » suffit
- [x] Une fiche du sujet « Vérification sans test » (TST-VER-…)
- [ ] Un Custom Test (TST-CUS-…) créé pour l'occasion
## Dans quel ordre un requirement avance-t-il dans son cycle ?
- [x] In Analysis → Accepted → Allocated → Implemented → In Verification
- [ ] Accepted → In Analysis → Implemented → Allocated → In Verification
- [ ] Allocated → Accepted → In Analysis → In Verification → Implemented
## Vous réimportez une spec client complétée dans Excel. Que montre l'aperçu ?
- [ ] Le nombre de lignes créées, modifiées et refusées seulement
- [x] Chaque valeur qui serait remplacée, à décocher pour la garder
- [ ] Les lignes refusées seulement ; les autres sont déjà écrites
## Vous filtrez 12 requirements sur 150, puis « Exporter la sélection ». Que contient le fichier ?
- [x] Les 12 lignes affichées
- [ ] Les 150 requirements du Space
- [ ] Les 12 lignes et toutes leurs questions client
## Quand un requirement peut-il quitter « Customer Clarification » ?
- [ ] Dès qu'une première réponse arrive
- [x] Quand toutes ses questions sont closes
- [ ] Quand un administrateur le force
## Quelle question au client est la plus efficace ?
- [ ] « Quelle tension voulez-vous ? »
- [x] « 180 °C ± 10 °C à la buse ? »
- [ ] « Pouvez-vous préciser l'exigence 12 ? »
> Une question fermée qui propose une valeur : le client n'a qu'à confirmer.
## Que contient l'export Word d'une spécification Goldmine ?
- [x] Une page de garde et une table des matières
- [x] Un bloc par requirement et une matrice de traçabilité
- [x] Les Definitions et Acronyms
- [ ] Les feuilles de temps du projet
## Dans « Test Procedure », pourquoi certains sujets portent-ils une ★ ?
- [x] Ils conviennent à la category et à la phase du requirement
- [ ] Ce sont les tests déjà cités par d'autres requirements du Space
- [ ] Ce sont les tests de category Standard, préférés aux Custom Tests
## Que veut dire le Need Status « Assumption » ?
- [x] Une hypothèse de l'équipe, pas encore confirmée par le client
- [ ] Un besoin contractuel
- [ ] Un besoin rejeté
> Customer Confirmed et Contractual sont des besoins fermes du client.
## Où un requirement indique-t-il les fonctions du produit qu'il sert ?
- [x] Dans le champ « Functions » (codes F-XX de la liste centrale)
- [ ] Dans son titre
- [ ] Dans le champ Rationale
"""

HL_05 = """# Quiz : Exploration — planifier
pass: 80
## Qu'est-ce que le plan d'Exploration, par rapport aux tickets Agile ?
- [x] Un plan abstrait, volontairement séparé des tickets
- [ ] Les tickets Agile du Space, regroupés par sprint sur un Gantt
- [ ] Une copie du backlog, mise à jour chaque nuit avec les dates
## En quelle unité les durées des tâches sont-elles données ?
- [ ] En jours ouvrables
- [x] En semaines
- [ ] En heures
## Comment les dates du plan sont-elles obtenues ?
- [ ] Chaque responsable saisit les dates de début et de fin de ses tâches
- [x] Elles se calculent à partir des durées et des prédécesseurs
- [ ] Elles viennent des dates de début et de fin des sprints Agile
## Vous rendez la tâche A prédécesseur de B, et B prédécesseur de A. Que se passe-t-il ?
- [x] C'est refusé : une boucle de prédécesseurs n'est pas permise
- [ ] Les deux tâches démarrent en même temps
- [ ] Le Gantt affiche les deux tâches en rouge mais garde le lien
## Comment le retard est-il montré ?
- [ ] Par un courriel au responsable
- [x] En rouge sur le Gantt
- [ ] Par un ticket Agile créé automatiquement
## Que met à jour le responsable d'une tâche ?
- [x] Son status
- [x] Son avancement
- [x] Une note de suivi
- [ ] Le début du plan
> Le début du plan et la création des tâches reviennent à un administrateur.
## Vous cliquez « + Task » sur l'en-tête d'une phase. Où va la tâche ?
- [ ] Au début du plan
- [x] À la fin de cette phase
- [ ] Dans une nouvelle phase
## Qui peut utiliser « ✎ Mode édition » pour réordonner le plan ?
- [ ] Tout Éditeur du Space
- [x] Les administrateurs
- [ ] Le responsable de la tâche
## En mode édition, vous glissez une tâche par sa poignée ⠿ jusqu'au bord de sa phase. Que se passe-t-il ?
- [x] Elle passe dans la phase voisine ; ses dates restent calculées
- [ ] Elle prend la date de début de l'endroit où vous l'avez lâchée
- [ ] Elle reste dans sa phase : le glisser ne fait que réordonner
## Quelle est la façon recommandée de bâtir un gros plan ?
- [ ] Créer chaque tâche à la main avec « + Task »
- [x] « Exporter Excel », travailler le plan dans Excel, puis « Importer… »
- [ ] Copier les tickets Agile un par un
## Le classeur Excel exporté contient une feuille « Lisez-moi ». Pour qui est-elle écrite ?
- [x] Pour vous, et aussi pour un agent IA
- [ ] Pour l'IT, qui importe le plan sur le serveur
- [ ] Pour le client, à qui on envoie le plan
## Où trouve-t-on une consigne prête à copier pour qu'un agent IA prépare le plan ?
- [x] Dans Import / Export d'Exploration
- [ ] Dans Help → FAQ seulement
- [ ] Dans Admin → Configuration
## Quelle question Exploration aide-t-il à répondre ?
- [ ] Que doit faire le produit ?
- [x] Quand, dans les grandes lignes ?
- [ ] Qui fait quoi, maintenant ?
> Goldmine : quoi ; Exploration : quand (phases, semaines) ; Agile : qui, maintenant (ticket, sprint).
## Que filtre « Mes tâches » ?
- [x] Les tâches dont vous êtes responsable
- [ ] Les tâches en retard de tout le Space
- [ ] Les tâches de la semaine en cours
## Quels formats acceptent l'import et l'export du plan ?
- [x] Excel .xlsx ou CSV
- [ ] PDF seulement
- [ ] Word .docx
"""
