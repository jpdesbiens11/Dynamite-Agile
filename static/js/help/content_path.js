/* Help - the chronological path (D-B-024), « tour du site » 0.47.0 (D-B-092): the chapters follow the top bar
   (Dashboard, Accueil | Goldmine, Exploration, Agile, Dynamite, Testing | Tools, Training, Timesheet) and the order a
   product is developed. Each chapter ends with its DEMO exercise (ticket found by chapter id, modules/help/tour.py).
   Content only (data), rendered by help.js with textContent -- never HTML.
   Blocks: ["p", text] ["h", text] ["steps", [..]] ["list", [..]] ["tip", text] ["warn", text]
   ["table", [header], [[row]...]]. **bold** is the only inline markup. The chapters of Testing, Tools, Training and
   Admin are in content_path2.js (files stay under 500 lines). */
(function () {
  "use strict";

  const HELP = (DA.help = DA.help || {});

  HELP.path = [
    { id: "bienvenue", title: "Bienvenue, barre du haut et réglages", tool: "Accueil",
      summary: "Ce qu'est la plateforme, la barre du haut dans l'ordre, votre compte, vos thèmes.",
      blocks: [
        ["p", "Dynamite | Agile réunit les outils de conception de produit en un seul endroit, sur le serveur de l'équipe : **une connexion, "
          + "tous les outils**, les mêmes Spaces partout. Rien ne part vers un service externe. Nouveau ? La page de connexion "
          + "a un lien « Découvrez la plateforme en 3 minutes » (page vitrine)."],
        ["h", "La barre du haut, dans l'ordre d'usage"],
        ["table", ["Groupe", "Onglet", "À quoi il sert"], [
          ["Vous", "Dashboard", "Tout ce qui vous attend, dans tous vos Spaces, et vos Messages (@mentions)"],
          ["Vous", "Accueil", "Vos Spaces, votre rôle dans chacun, « Qui contacter ? »"],
          ["Planifier → construire → vérifier", "Goldmine", "Needs des stakeholders et requirements d'ingénierie, traçabilité jusqu'au test"],
          ["", "Exploration", "Plan sur plusieurs mois (Gantt)"],
          ["", "Agile", "Backlog, Sprints, Board ; Change Management (PR, bugs, ECN)"],
          ["", "Dynamite", "Wiki : pages, procédures, Base de connaissances (BDC)"],
          ["", "Testing", "Test Base (sécurité électrique, CEM, IP, chute, durée de vie…), procédures, Test Plans fournisseurs, listes centrales"],
          ["Soutien", "Tools", "Design (idéation, Pugh, Kepner-Tregoe…) et Generator (références de documents)"],
          ["", "Training", "Topics de formation, votre plan de l'année, tests"],
          ["", "Timesheet", "Feuille de temps hebdomadaire, approbations, exports"],
          ["À droite", "Recherche · Ctrl K · Mes éléments · Liste Audit · Audit · Help", "Retrouver, aller vite, filtrer sur vous, signaler, apprendre"],
          ["Tout à droite", "Menu à votre nom · ⚙ Admin", "Vos pages personnelles et vos thèmes · l'administration (administrateurs)"]]],
        ["tip", "Survolez un onglet : une bulle dit à quoi il sert. Sur un petit écran, les onglets se compactent en icônes."],
        ["steps", [
          "À la première connexion, choisissez votre mot de passe (au moins 12 caractères). Plus tard : menu à votre nom → « Changer mon mot de passe ».",
          "Donnez votre **clé de traçabilité de 3 lettres** (vos initiales) : menu à votre nom → Paramètres → « Mes initiales ». Sans elle, aucune écriture n'est acceptée (bandeau jaune « Initiales requises »).",
          "Sur l'**Accueil** : vos Spaces et votre rôle dans chacun, puis « Qui contacter ? » (qui s'occupe de quoi).",
          "Rejoignez le Space **DEMO** (bouton dans le panneau de gauche de cette aide) : un bac à sable où tout peut être essayé sans risque."]],
        ["h", "Thèmes et réglages"],
        ["list", [
          "**Menu à votre nom → Thème** : **Thème par défaut** (croquis d'ingénieur, icônes dessinées à la main) ou **Terminal R&D** (labo geek, sombre, invite de commande et séquence de démarrage). Un clic, l'écran se redessine ; le choix vous suit sur tous vos postes.",
          "**Menu à votre nom → Paramètres** : les autres thèmes (Atlassian, Système, Clair, Sombre, Contraste élevé), police, taille du texte, densité, page d'ouverture, vos initiales et votre approbateur de feuilles de temps. L'outil est en français, termes techniques en anglais ; pour une autre langue, « Traduire » de votre navigateur.",
          "**Ctrl+K** (ou le bouton « Ctrl K » de la barre) : la palette. Tapez quelques lettres d'un onglet, d'un Space ou d'une page (« eqp gold » trouve Goldmine · EQP), Entrée pour y aller. La dernière ligne cherche partout.",
          "**Panneau de gauche** de chaque outil : glissez son bord pour l'élargir, ou masquez-le avec le bouton bleu « <<< » (« >>> » pour le rouvrir).",
          "**Space par défaut** : sur la page d'ouverture d'Agile, Goldmine, Dynamite, Testing ou Exploration, la marge gauche liste vos Spaces ; cochez-en un : chaque onglet s'ouvre directement sur lui. « ↺ Réinitialiser le Space par défaut » (bas de la liste) ramène à la liste ; dans un Space, « ▤ Tous les Spaces » y retourne.",
          "**[new]** à côté d'un champ ou d'un bouton : c'est une nouveauté de la dernière version. Le badge disparaît quand vous l'avez utilisé (ou rempli).",
          "**Menu à votre nom → Mes objectifs** : l'évaluation de l'année en 3 étapes signées par vous et votre gestionnaire — Début d'année (objectifs annuels, de développement et de formation), Mi-année (un commentaire de chacun sur chaque item), Fin d'année (un verdict sur chaque item). Pour un stagiaire : Accueil, Mi-stage et Évaluation finale avec grille de compétences.",
          "**Profil et parcours** : titre, niveau et dates fixés par le gestionnaire, en tête de chaque évaluation ; votre formation et vos expériences, remplies par vous.",
          "**Menu à votre nom → Mon équipe** (gestionnaires) : une carte par personne qui vous a choisi, ses 3 étapes, qui a signé et ce qui vous attend (« À vous : relire et signer »). Chaque signature envoie un message à l'autre partie dans le Dashboard → Messages."]],
        ["tip", "Mot de passe oublié : un administrateur vous en donne un temporaire (Admin → Utilisateurs)."]] },

    { id: "dashboard", isNew: true, title: "Dashboard et Messages (@mentions)", tool: "Dashboard",
      summary: "Ce qui vous attend partout ; écrire à un collègue avec @identifiant.",
      blocks: [
        ["p", "Le **Dashboard** (premier onglet) est la page d'ouverture : tickets Agile, PR / ECN, requirements Goldmine, "
          + "questions client, tâches Exploration, items Training, feuille de temps, observations Audit."],
        ["list", [
          "**Changez un status sur place** (menu ▾ à droite de chaque élément : seules les étapes permises par le workflow sont proposées), ou cliquez **« Ouvrir EQP → »** : la bonne liste s'ouvre avec « Mes éléments » actif. Un clic sur un compteur descend à sa section.",
          "Bouton **Mes éléments** (barre du haut) : partout, n'affiche plus que vos tickets, vos requirements et vos tâches. Un clic de plus pour tout revoir."]],
        ["h", "Messages : les @mentions"],
        ["steps", [
          "Dans une page Dynamite, un commentaire, un ticket ou un requirement, tapez **@** : la liste des comptes s'ouvre ; choisissez la personne (ex. @jean-philippe).",
          "Elle reçoit un message dans son **Dashboard → Messages → Reçus**, avec le lien vers l'endroit exact ; la pastille du Dashboard compte les non lus.",
          "Vous le retrouvez dans **Messages → Envoyés**, avec Lu / Non lu.",
          "**Répondre ici** (sous un message reçu) : écrivez, « Envoyer la réponse ». La réponse est enregistrée en commentaire à l'endroit d'origine, signée par vous, avec « @demandeur » à la fin ; le message passe dans **Traités**. Le demandeur reçoit une **Réponse** et clique **Acknowledge** pour la retirer de son Dashboard.",
          "**@votre-identifiant** dépose une **Note** pour vous-même dans vos Messages (badge « Moi ») : pratique pour un rappel."]],
        ["tip", "Une personne qui n'a pas accès au Space n'est pas prévenue : le message d'enregistrement le dit (« n'a pas accès à ce Space »)."],
        ["p", "Administrateurs : « Voir le tableau de bord de » montre la charge d'un employé en lecture seule (journalisé) ; ses Messages restent privés."]] },

    { id: "projets", title: "Spaces, rôles et droits", tool: "Accueil",
      summary: "Lecteur, éditeur, administrateur : qui peut faire quoi.",
      blocks: [
        ["p", "Tout est rangé **par Space** (clé courte, ex. EQP). Vos droits sont donnés Space par Space :"],
        ["table", ["Rôle", "Peut"], [
          ["Lecteur", "Tout lire, commenter, poser des questions, exporter"],
          ["Éditeur", "Créer et modifier pages, tickets, requirements ; réserver des références"],
          ["Admin du Space", "Comme éditeur, et gérer les membres de ce Space (menu à votre nom → « Membres de mes Spaces »)"],
          ["Administrateur", "Tout, sur tous les Spaces ; créer Spaces et comptes ; approuver (CCB, feuilles de temps)"]]],
        ["list", [
          "Un ticket se modifie seulement par **son responsable** (l'assigné) ou un administrateur ; les autres le lisent et le commentent.",
          "Un ticket sans responsable se prend avec « Prendre le ticket ».",
          "Un Space par produit, autonome de Goldmine à Timesheet. Un seul Space commun : **DEMO**, le bac à sable et la bibliothèque de référence (catalogue d'essais, méthodes de Tools, formation, codes de temps).",
          "Un Space qui vous manque ? Demandez l'accès à un administrateur."]]] },

    { id: "goldmine", title: "Goldmine : capter les needs et les requirements", tool: "Goldmine",
      summary: "Needs, requirements, Test Procedure, import d'une spec, Q&A client, Pugh.",
      blocks: [
        ["p", "Goldmine garde les **needs** des stakeholders et les **requirements** d'ingénierie : statement, source, category, criticité, verification method (IADT), acceptance criteria, allocation, Functions et **Test Procedure** (le test qui la vérifie, obligatoire)."],
        ["steps", [
          "Goldmine → Space → « Requirements » : créez un requirement ou ouvrez-en un.",
          "**Functions** : rattachez-le à une ou plusieurs fonctions du produit (F-XX, tirées de l'analyse fonctionnelle ; page « Product Function Structure » de la BDC). Filtre « Function » dans la liste.",
          "**Test Procedure** : choisissez le test (ou les tests) de la Test Base qui le vérifie ; les sujets qui conviennent à sa category et à sa phase sont en tête (★), la **Test Source** se remplit seule. Sans test, le requirement ne s'enregistre pas (un need n'en a pas besoin).",
          "**Needs** : un need porte un **Need Status** (Assumption = hypothèse de l'équipe ; Customer Confirmed ou Contractual = besoin ferme). Chaîne : need du client → requirement → test (Derived From).",
          "Faites-le avancer dans son cycle (In Analysis → Accepted → Allocated → Implemented → In Verification…) ; tracez-le depuis le ticket Agile qui le réalise (lien « implémente »).",
          "Une spec client entière ? « Import / Export » → exportez le gabarit, remplissez-le dans Excel (ou par un agent IA approuvé), réimportez : un aperçu liste chaque valeur qui serait remplacée, décochez celles à garder, confirmez.",
          "Par petits lots : filtrez (phase, category, criticité, status, Need Status, texte…) ; le bandeau bleu compte la sélection et « Exporter la sélection » n'envoie que ces lignes.",
          "**Exporter en Word (.docx)** : les requirements affichés deviennent une spécification au gabarit Word (page de garde, table des matières, un bloc par requirement, matrice de traçabilité, Definitions et Acronyms)."]],
        ["h", "Q&A avec le client"],
        ["steps", [
          "Goldmine → « Q&A » : chaque question a sa référence (**Qteam-003** = question de l'équipe ; **Qcust-004** = question du client), sa date et ses initiales.",
          "Le filtre « À traiter par l'équipe » montre ce qui l'attend ; répondez dans la carte (Ctrl+Entrée), J / K pour passer à la suivante.",
          "« ⇩ Exporter les Q&R (Excel) » pour le client, « ⇧ Importer les Q&R » au retour (vérification à blanc, puis « Appliquer »). « 🗄 Archives des échanges » garde chaque fichier.",
          "Un requirement ne quitte « Customer Clarification » que quand toutes ses questions sont closes."]],
        ["tip", "Posez des questions fermées : proposez une valeur (« 180 °C ± 10 °C à la buse ? ») que le client n'a qu'à confirmer."],
        ["p", "**Matrices de Pugh** (Goldmine, ou Tools → Design) : comparer des concepts à un Datum sur des criteria pondérés, export Excel."]] },

    { id: "exploration", title: "Exploration : planifier", tool: "Exploration",
      summary: "Plan sur plusieurs mois, Gantt, aller-retour Excel.",
      blocks: [
        ["p", "Exploration porte le **plan abstrait** du Space (phases, tâches, prédécesseurs, durées en semaines, responsables), volontairement séparé des tickets Agile."],
        ["steps", [
          "Un administrateur fixe le début du plan et crée les tâches (« + Task »), ou mieux : « Exporter Excel », travaille le plan dans Excel, puis « Importer… ».",
          "Les dates se calculent seules (fin → début) ; une boucle de prédécesseurs est refusée. Le retard est en rouge sur le Gantt.",
          "Chaque responsable met à jour **ses** tâches : status, avancement, note de suivi. « Mes tâches » filtre les vôtres.",
          "« + Task » sur l'en-tête d'une phase ajoute une tâche **à la fin de cette phase**.",
          "**« ✎ Mode édition »** (administrateurs) : glissez une ligne par sa poignée ⠿ ou utilisez ↑ ↓ ; au bord de sa phase, elle passe dans la phase voisine. Les dates suivent toujours durées et prédécesseurs."]],
        ["tip", "Import / Export contient une **consigne prête à copier** pour qu'un agent IA prépare ou corrige le fichier Excel du plan."]] },

    { id: "agile", title: "Agile : exécuter", tool: "Agile",
      summary: "Backlog, sprints, Board, tickets, questions client.",
      blocks: [
        ["steps", [
          "« Créer un ticket » : type (epic, task…), titre, description, priority, responsable. Le créateur en devient responsable par défaut.",
          "**Backlog** (premier lien du panneau de gauche) : ordonnez le travail (glisser-déposer), préparez un sprint, puis « Démarrer le sprint ».",
          "**Board** : chaque responsable déplace sa carte d'une colonne à l'autre selon le workflow du Space.",
          "Dans un ticket : commentaires (cochez « Question » pour une question au client, @collègue pour le prévenir), liens (bloque, implémente…), synthèse client.",
          "« Tickets » : liste filtrable ; **⚙ Admin → Paramètres du Space** (administrateurs) : workflows, types, labels, versions."]],
        ["p", "La méthode pas à pas, avec captures : Dynamite → DEMO → Base de connaissances → « Guide de la méthode Agile »."],
        ["h", "Import / Export"],
        ["p", "Tickets et questions client s'échangent en CSV lisible par Excel. Partez **toujours d'un export**, modifiez, réimportez : une ligne inchangée ne change rien, une ligne refusée est listée avec son numéro de ligne Excel et le correctif."]] },

    { id: "changements", title: "Change Management : PR, bugs, ECN", tool: "Agile",
      summary: "Du problème à l'ECN approuvé par le CCB.",
      blocks: [
        ["steps", [
          "Un problème (PR) ou un bug logiciel s'ouvre dans Agile → « Change Management ».",
          "Analysez-le (sévérité, confinement, cause racine), puis « Derive to ECN » si un changement est nécessaire.",
          "L'ECN décrit le changement (classe, raison, impacts forme-ajustement-fonction, certification, sécurité) et ses **Affected Items** (révision actuelle → nouvelle).",
          "« Submit to CCB » ; un administrateur du Space approuve ou rejette (approbateurs nommés).",
          "Implantation puis vérification (toutes les sub-tasks terminées) avant la fermeture."]],
        ["tip", "Chaque étape bloquée affiche ce qui manque (ex. « au moins un Affected Item »)."]] },

    { id: "dynamite", title: "Dynamite : documenter", tool: "Dynamite",
      summary: "Pages, éditeur visuel, blocs vivants, import d'une IA, export PDF / Word.",
      blocks: [
        ["p", "Chaque Space a son wiki Dynamite, ouvert sur une **page d'accueil** créée avec le Space (objet, équipe, jalons, accès rapides)."],
        ["steps", [
          "Ouvrez le wiki (Dynamite → Space), puis « + Nouvelle page » ou, sur une page, « + Sous-page ».",
          "Écrivez dans l'éditeur **visuel** (barre d'outils, ou « / » pour le menu des blocs). Le mode **Source** accepte une syntaxe courte.",
          "Insérez des blocs utiles : tableau, panneau (info, note, avertissement, succès), status coloré, **bloc Ticket** vivant ([[EQP-12]]), table des matières, sous-pages, image collée.",
          "Enregistrez (Ctrl+S). Chaque enregistrement crée une **version** ; « Historique » compare et restaure.",
          "Discutez sous la page (commentaires, @collègue), sans toucher au texte.",
          "**Déplacer / Copier** une page (et ses sous-pages) vers un autre Space ; **Export PDF / Word** de la page ou de toute la branche (droit d'export donné par compte)."]],
        ["h", "Importer d'une IA"],
        ["p", "« ✨ Importer d'une IA » (ou menu « / ») : collez la réponse d'un agent IA (Markdown, HTML ou texte), vérifiez l'aperçu, insérez au curseur ou remplacez la page. Titres, listes, tableaux, code, liens et encadrés « > [!NOTE] » sont conservés."],
        ["h", "Base de connaissances (BDC)"],
        ["p", "Dans DEMO → Dynamite : Getting Things Done, Product Function Structure (F-XX), Definitions et Acronyms, guide de la méthode Agile, « Mettre à jour le site (Admin → Update) »."],
        ["warn", "Une page vient d'être modifiée par un collègue pendant que vous éditiez ? L'enregistrement est refusé avec le nom de l'auteur : copiez votre texte, rechargez, réappliquez."]] },
  ];
})();
