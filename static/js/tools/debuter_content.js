/* Dynamite | Agile - « Débuter » content (0.60.08): the path of a project through the platform, in the order of the
   product development process (PDP) taught in the design course -- before the project, A. Pré-étude, B. Étude
   conceptuelle, C. Conception, D. Fabrication et validation du prototype, then what runs all along.
   Each step: [module key for the icon, title, text, [[button label, hash, view?], ...], admin-only?]. A link with a view
   opens it in the person's default Space (D-B-098); without a default Space, the tab offers the list. Plain data, built with el() by debuter.js. */
(function () {
  "use strict";

  DA.debuterContent = [
    { id: "avant", kicker: "Avant le projet", title: "S'installer et former l'équipe",
      text: "Une fois l'outil installé, l'administrateur crée le projet ; chacun règle son poste et découvre l'outil sans rien casser.",
      steps: [
        ["admin", "Démarrer le projet avec un assistant IA",
          "Un assistant IA vous pose des questions sur votre produit, votre industrie et votre marché, puis donne un fichier qui crée le "
          + "Space : l'équipe et son profil d'études, les besoins et requirements, les essais alignés sur les normes, les codes de temps et "
          + "les premières pages. Sans assistant : créez le Space et les comptes à la main.",
          [["Commencer", "#/admin/start"], ["Créer un Space", "#/admin/projects"], ["Comptes", "#/admin/users"]], true],
        ["help", "Prendre ses repères",
          "Changez votre mot de passe temporaire, donnez vos initiales, choisissez votre thème et votre page d'arrivée. Le bac à sable "
          + "HeadLamp et le guide montrent chaque outil sur un projet fictif.",
          [["Paramètres", "#/settings"], ["Guide et HeadLamp", "#/help"]]],
        ["home", "Trouver son Space",
          "L'Accueil liste vos Spaces et qui contacter pour quoi. Choisissez votre Space par défaut : chaque onglet s'ouvrira dessus.",
          [["Accueil", "#/home"]]],
      ] },
    { id: "A", kicker: "Phase A · étapes 1 à 6", title: "Pré-étude", deliverable: "MIP (mémoire d'identification de projet)",
      text: "Comprendre le marché et le client, définir le projet, son échéancier, son budget et ses risques.",
      steps: [
        ["goldmine", "Recueillir les besoins du client",
          "Notez chaque besoin (Need) avec la partie prenante qui l'exprime, et posez vos questions au client dans le registre Q&A : "
          + "ses réponses restent liées au besoin.",
          [["Goldmine", "#/goldmine"], ["Q&A", "#/goldmine", "qa"]]],
        ["exploration", "Planifier le projet",
          "Bâtissez l'échéancier dans Exploration : phases, tâches, jalons et responsables, sur un Gantt que toute l'équipe voit.",
          [["Plan", "#/exploration", "plan"]]],
        ["dynamite", "Rédiger le MIP",
          "Le wiki Dynamite garde vos documents vivants, avec leurs versions et commentaires. Le Generator donne au MIP sa référence, "
          + "son nom de fichier et son dossier.",
          [["Dynamite", "#/dynamite"], ["Generator", "#/tools/generator"]]],
      ] },
    { id: "B", kicker: "Phase B · étapes 7 à 12", title: "Étude conceptuelle", deliverable: "RCS (rapport de conception système)",
      text: "Des besoins aux fonctions, des fonctions aux spécifications, puis la recherche et le choix des concepts.",
      steps: [
        ["goldmine", "Écrire le cahier des charges",
          "Dérivez les requirements des besoins : énoncé, critère d'acceptation, méthode de vérification et norme. Une norme proposée "
          + "par un assistant IA reste « À vérifier » jusqu'à ce qu'une personne confirme son édition.",
          [["Requirements", "#/goldmine"]]],
        ["tools", "Chercher les concepts",
          "Brainstorming, brainwriting et carte mentale pour diverger ; la matrice de Pugh et l'analyse Kepner-Tregoe pour choisir, "
          + "avec la méthode et une FAQ à côté de chaque outil.",
          [["Tools · Design", "#/tools/design"]]],
        ["dynamite", "Consigner l'analyse fonctionnelle",
          "Arbre fonctionnel, structure fonctionnelle et notes à la conception dans le wiki ; le RCS rassemble l'étude conceptuelle.",
          [["Dynamite", "#/dynamite"]]],
      ] },
    { id: "C", kicker: "Phase C · étapes 13 à 15", title: "Conception", deliverable: "RC (rapport de conception)",
      text: "Découper en sous-systèmes, les concevoir et suivre le travail de l'équipe, Sprint après Sprint.",
      steps: [
        ["agile", "Organiser le travail",
          "Un ticket par tâche de conception, rangé dans le Backlog puis dans un Sprint ; le Board montre qui fait quoi.",
          [["Backlog", "#/agile", "backlog"], ["Board", "#/agile", "board"]]],
        ["agile", "Gérer les changements",
          "Une modification d'une conception figée passe par Change Management : demande (PR), avis de changement (ECN) et suivi.",
          [["Change Management", "#/agile", "changes"]]],
        ["dynamite", "Documenter la conception",
          "Calculs, choix de matériaux et revues de conception dans le wiki ; le RC suit la structure des sous-systèmes.",
          [["Dynamite", "#/dynamite"], ["Generator", "#/tools/generator"]]],
      ] },
    { id: "D", kicker: "Phase D · étapes 19 à 21", title: "Fabrication et validation du prototype",
      deliverable: "RVE (rapport de validation expérimentale)",
      text: "Fabriquer le prototype et prouver que chaque requirement est respecté.",
      steps: [
        ["testing", "Préparer les essais",
          "Chaque requirement nomme l'essai qui le vérifie dans la Test Base ; écrivez les procédures et, pour un laboratoire externe, "
          + "un Test Plan.",
          [["Testing", "#/testing"]]],
        ["goldmine", "Fermer la boucle",
          "Une fois l'essai passé, inscrivez la référence du rapport et passez le requirement à « Verified » : Goldmine montre ce "
          + "qui reste à prouver.",
          [["Goldmine", "#/goldmine"]]],
        ["dynamite", "Rédiger le RVE",
          "Résultats, écarts et conclusions dans le wiki, exportables en Word et en PDF.",
          [["Dynamite", "#/dynamite"]]],
      ] },
    { id: "continu", kicker: "Tout au long du projet", title: "Chaque semaine",
      text: "Ce qui accompagne toutes les phases.",
      steps: [
        ["dashboard", "Voir ce qui vous attend",
          "Le Dashboard rassemble vos tickets, requirements, tâches du plan et messages (@mentions), dans tous vos Spaces.",
          [["Dashboard", "#/dashboard"]]],
        ["timesheet", "Saisir ses heures",
          "Ma semaine, avec les codes de temps du projet ; le gestionnaire approuve, l'administrateur exporte le rapport.",
          [["Timesheet", "#/timesheet"]]],
        ["training", "Se former",
          "Votre plan de formation, ses topics et leurs tests, et vos objectifs de mi-année et de fin d'année.",
          [["Training", "#/training"]]],
        ["admin", "Garder une trace",
          "Révisions figées du projet, sauvegardes et journal d'audit, pour retrouver l'état d'une remise.",
          [["Révisions", "#/admin/revisions"], ["Sauvegardes", "#/admin/update/data"]], true],
      ] },
  ];
})();
