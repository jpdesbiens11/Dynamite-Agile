/* Dynamite | Agile - « Débuter » content (0.60.08; Lean Startup since 0.60.09, D-O-021): the path of a project through the
   platform, along the PDP of the design course modernised -- before the project, A. Discovery, B. Concept, C. Design,
   D. Validation et lancement, then what runs all along. Each phase is a Build-Measure-Learn loop: its MVP tests the riskiest
   hypotheses, Agile Sprints pace the hardware and software work, and the phase ends on an industry review with the
   decision to persevere or pivot -- one turn of the « tornado » drawn by debuter.js.
   Each step: [module key for the icon, title, text, [[button label, hash, view?], ...], admin-only?]. A link with a view
   opens it in the person's default Space (D-B-098); without a default Space, the tab offers the list. Plain data, built
   with el() by debuter.js. Phase fields mvp and review feed the tornado legend. */
(function () {
  "use strict";

  DA.debuterContent = [
    { id: "avant", kicker: "Avant le projet", title: "S'installer et former l'équipe",
      text: "Une fois l'outil installé, l'administrateur crée le projet ; chacun règle son poste et découvre l'outil sans rien casser.",
      steps: [
        ["admin", "Démarrer le projet avec un assistant IA",
          "Commencer → « Copier le prompt », à coller dans Claude.ai ou un autre assistant : il vous pose une vingtaine de questions sur votre produit, votre industrie et votre marché, puis donne un fichier qui crée le "
          + "Space : l'équipe et son profil d'études, les besoins et requirements, les essais alignés sur les normes, les codes de temps et "
          + "les premières pages. Sans assistant : créez le Space et les comptes à la main.",
          [["Commencer", "#/admin/start"], ["Créer un Space", "#/admin/projects"], ["Comptes", "#/admin/users"]], true],
        ["help", "Prendre ses repères",
          "Changez votre mot de passe temporaire, vérifiez vos initiales (données d'après votre nom), choisissez votre thème et votre page d'arrivée. Le bac à sable "
          + "DEMO et le guide montrent chaque outil sur un projet fictif.",
          [["Paramètres", "#/settings"], ["Guide et DEMO", "#/help"]]],
        ["home", "Trouver son Space",
          "L'Accueil liste vos Spaces et qui contacter pour quoi. Choisissez votre Space par défaut : chaque onglet s'ouvrira dessus.",
          [["Accueil", "#/home"]]],
      ] },
    { id: "A", kicker: "Phase A · étapes 1 à 6 · MVP 0", title: "Discovery", mvp: "MVP 0 : le problème existe-t-il ?",
      review: "Lean Canvas et hypothèses", deliverable: "Lean Canvas et hypothèses à tester (LCV)",
      text: "Comprendre le client et son problème avant de concevoir : un MVP 0 (entrevues, maquette papier, page d'essai) vérifie "
        + "que le problème est réel et que quelqu'un veut une solution.",
      steps: [
        ["goldmine", "Recueillir les besoins du client",
          "Notez chaque besoin (Need) avec la partie prenante qui l'exprime, et posez vos questions au client dans le registre Q&A : "
          + "ses réponses restent liées au besoin.",
          [["Goldmine", "#/goldmine"], ["Q&A", "#/goldmine", "qa"]]],
        ["dynamite", "Remplir le Lean Canvas",
          "Problème, segments de clients, proposition de valeur, solution, métriques clés, coûts : une page dans le wiki, puis la "
          + "liste des hypothèses les plus risquées que le MVP 0 doit tester. Le Generator lui donne sa référence (LCV).",
          [["Dynamite", "#/dynamite"], ["Generator", "#/tools/generator"]]],
        ["exploration", "Planifier les boucles",
          "Dans Exploration, une phase par boucle : construire le MVP, mesurer, apprendre, avec la revue de fin de phase comme jalon.",
          [["Plan", "#/exploration", "plan"]]],
      ] },
    { id: "B", kicker: "Phase B · étapes 7 à 12 · MVP 1", title: "Concept", mvp: "MVP 1 : le concept plaît-il ?",
      review: "Concept Review", deliverable: "Concept Review (CRV)",
      text: "Des besoins aux fonctions, des fonctions aux spécifications, puis les concepts. Le MVP 1 (maquette d'apparence, "
        + "simulation, prototype rapide) les met devant de vrais utilisateurs.",
      steps: [
        ["goldmine", "Bilan du MVP 0 : persévérer ou pivoter",
          "Ce que le MVP 0 a appris confirme le problème ou le fait changer : notez la décision et ce qu'elle change dans les besoins.",
          [["Goldmine", "#/goldmine"]]],
        ["goldmine", "Écrire le cahier des charges",
          "Dérivez les requirements des besoins : énoncé, critère d'acceptation, méthode de vérification et norme. Une norme proposée "
          + "par un assistant IA reste « À vérifier » jusqu'à ce qu'une personne confirme son édition.",
          [["Requirements", "#/goldmine"]]],
        ["tools", "Chercher et choisir les concepts",
          "Brainstorming, brainwriting et carte mentale pour diverger ; la matrice de Pugh et l'analyse Kepner-Tregoe pour choisir, "
          + "avec la méthode et une FAQ à côté de chaque outil.",
          [["Tools · Design", "#/tools/design"]]],
        ["dynamite", "Préparer la Concept Review",
          "Analyse fonctionnelle, concepts retenus et résultats du MVP 1 dans le wiki ; la revue décide de passer en Design.",
          [["Dynamite", "#/dynamite"], ["Generator", "#/tools/generator"]]],
      ] },
    { id: "C", kicker: "Phase C · étapes 13 à 15 · MVP 2", title: "Design", mvp: "MVP 2 : ça fonctionne ?",
      review: "PDR puis CDR", deliverable: "Preliminary et Critical Design Review (PDR, CDR)",
      text: "Découper en sous-systèmes et les concevoir, Sprint après Sprint, en matériel comme en logiciel. Le MVP 2 est le "
        + "premier prototype qui fonctionne.",
      steps: [
        ["agile", "Organiser les Sprints matériel et logiciel",
          "Un ticket par tâche de conception, rangé dans le Backlog puis dans un Sprint de deux à trois semaines ; le Board montre qui "
          + "fait quoi. Une itération matérielle livre une pièce, un montage ou un essai, pas seulement du code.",
          [["Backlog", "#/agile", "backlog"], ["Board", "#/agile", "board"]]],
        ["agile", "Gérer les changements",
          "Une modification d'une conception figée passe par Change Management : demande (PR), avis de changement (ECN) et suivi.",
          [["Change Management", "#/agile", "changes"]]],
        ["dynamite", "Passer la PDR, puis la CDR",
          "La Preliminary Design Review fige l'architecture des sous-systèmes ; la Critical Design Review, après le MVP 2, autorise "
          + "la fabrication. Calculs, AMDEC et décisions restent dans le wiki.",
          [["Dynamite", "#/dynamite"], ["Generator", "#/tools/generator"]]],
      ] },
    { id: "D", kicker: "Phase D · étapes 19 à 21 · MVP 3", title: "Validation et lancement", mvp: "MVP 3 : prêt pour le marché ?",
      review: "Validation Report", deliverable: "Validation Report (VVR, vérification et validation)",
      text: "Fabriquer le MVP 3, proche de la pré-série, prouver chaque requirement et le mettre entre les mains d'utilisateurs "
        + "pilotes avant le lancement.",
      steps: [
        ["testing", "Préparer les essais",
          "Chaque requirement nomme l'essai qui le vérifie dans la Test Base ; écrivez les procédures et, pour un laboratoire externe, "
          + "un Test Plan.",
          [["Testing", "#/testing"]]],
        ["goldmine", "Fermer la boucle",
          "Une fois l'essai passé, inscrivez la référence du rapport et passez le requirement à « Verified » : Goldmine montre ce "
          + "qui reste à prouver.",
          [["Goldmine", "#/goldmine"]]],
        ["dynamite", "Rédiger le Validation Report",
          "Vérification (le produit respecte les requirements) et validation (il répond au besoin des utilisateurs pilotes), écarts "
          + "et décision de lancement, exportables en Word et en PDF.",
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
