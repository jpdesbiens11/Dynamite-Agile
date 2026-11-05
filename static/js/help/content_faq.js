/* Help - FAQ (D-B-024): what is not intuitive and everyone should know,
   above all the round trip of data with Excel / CSV and how an AI agent (LLM)
   can prepare that data quickly. Same block format as content_path.js. */
(function () {
  "use strict";

  const HELP = (DA.help = DA.help || {});

  HELP.faq = [
    { q: "Peut-on sortir les données, les travailler ailleurs, puis les remettre ? (le va-et-vient)",
      blocks: [
        ["p", "Oui, c'est voulu : la base reste la référence, mais on peut **exporter → modifier dans Excel → réimporter**. Règle d'or : partez toujours d'un export récent."],
        ["table", ["Données", "Où", "Sortir", "Rentrer"], [
          ["Tickets", "Agile → Import / Export", "CSV", "CSV (création, mise à jour, inchangé)"],
          ["Questions / réponses client", "Agile → Import / Export", "CSV", "CSV (ajout de réponses seulement)"],
          ["Requirements", "Goldmine → Import / Export", "CSV", "CSV (une spec entière d'un coup ; colonne « test_ref » = Test Procedure)"],
          ["Tests", "Testing", "CSV ou Word .docx (sélection filtrée)", "CSV (aperçu, puis appliquer)"],
          ["Spécification de requirements", "Goldmine → Exporter en Word", "Word .docx (gabarit de l'outil)", "—"],
          ["Plan", "Exploration → Import / Export", "Excel .xlsx ou CSV", "Excel .xlsx ou CSV (plan complet)"],
          ["Changements (PR, ECN)", "Agile → Import / Export", "CSV", "—"],
          ["Références de documents", "Tools → Generator → Registre", "CSV", "—"],
          ["Heures", "Timesheet → Export Excel (admin)", "Excel .xlsx", "—"],
          ["Comptes et droits", "Admin → Règles d'accès", "Texte", "Texte (vérifié à blanc)"],
          ["Observations Audit", "Liste Audit (barre du haut)", "CSV", "—"],
          ["Pages", "Dynamite", "PDF / Word (droit d'export), ou copier le texte", "« Importer d'une IA » (Markdown, HTML, texte)"],
          ["Test Plans fournisseur", "Testing → Test Plans", "Word .docx (gabarit de l'outil)", "PDF des résultats"],
          ["Code du site (sans données)", "Admin → Update et sauvegardes → Framework", "Zip pour Claude", "Zip vérifié puis appliqué"]]],
        ["list", [
          "Un import est **vérifié avant d'écrire** : chaque ligne refusée est nommée avec son numéro de ligne Excel et le correctif ; rien n'est écrit pour elle.",
          "Réimporter le même fichier ne change rien (lignes « inchangée »).",
          "Si quelqu'un a modifié un ticket entre votre export et votre import, la ligne est refusée en nommant les champs en conflit : réexportez."]]] },

    { q: "Comment un agent IA (LLM) peut-il m'aider à remplir la plateforme rapidement ?",
      blocks: [
        ["p", "L'IA prépare, **vous vérifiez et vous importez**. Elle ne se connecte jamais à la plateforme."],
        ["steps", [
          "Exportez le fichier de départ (gabarit de requirements, plan Exploration, tickets…).",
          "Donnez-le à l'agent avec une consigne claire. Exploration fournit une consigne prête à copier ; le classeur Excel a une feuille « Lisez-moi » écrite aussi pour les agents IA.",
          "Relisez le résultat, puis importez-le : la vérification à blanc signale ce que l'IA a mal rempli.",
          "Pour une page : demandez un texte en Markdown, copiez-le avec le bouton « Copier » de l'agent, puis Dynamite → « ✨ Importer d'une IA »."]],
        ["warn", "Données contrôlées ou confidentielles (défense, client, export contrôlé) : utilisez **seulement un outil IA approuvé par votre établissement ou votre client**. Ne collez jamais ces données dans un agent IA public."]] },

    { q: "Pourquoi mon requirement ne s'enregistre pas (« Test Procedure » obligatoire) ?",
      blocks: [
        ["p", "Chaque requirement doit nommer au moins un test de la base **Testing** qui la vérifie : c'est ce qui garantit qu'aucune requirement n'arrive en campagne de tests sans moyen de preuve. Choisissez-le dans « Test Procedure » (liste par sujet). Une inspection, une analyse ou une démonstration a aussi sa fiche (sujet « Vérification sans test », TST-VER-…). Pour un need particulier, un « Custom Test » (TST-CUS-…), ou demandez à l'équipe de tests d'en créer un. Un requirement enregistrée avant cette règle apparaît dans « À compléter » (sans Test Procedure) et doit recevoir son test à sa prochaine modification. Un besoin n'a pas de test."]] },

    { q: "Il manque un équipement, un lieu ou une fonction dans la liste : que faire ?",
      blocks: [["p", "Les listes sont centrales pour éviter les variantes (« pot vibrant », « shaker », « table vib »…). Demandez l'ajout à un Admin du Space HeadLamp (la bibliothèque de référence) : Testing → Listes → « + Ajouter » (code court et stable, ex. EQ-HALT). Une entrée remplacée se désactive : elle reste sur les tests qui l'ont, mais n'est plus proposée. Les fonctions sont aussi publiées dans la page « Product Function Structure (F-XX) » de la Base de connaissances (BDC)."]] },

    { q: "Pourquoi je ne peux pas modifier ce ticket ?",
      blocks: [["p", "Un ticket se modifie par **son responsable** (l'assigné) ou un administrateur. Vous pouvez le commenter ; s'il n'a pas de responsable, « Prendre le ticket ». Pour le confier à quelqu'un d'autre, le responsable change l'assigné."]] },

    { q: "Pourquoi ma semaine ne se soumet pas ?",
      blocks: [["p", "Au moins une plage n'a pas de description (bordure rouge), ou la semaine est vide. Écrivez une courte description pour chaque plage. Une semaine approuvée est verrouillée : demandez à un administrateur de la rouvrir."]] },

    { q: "Où retrouver les observations Audit envoyées, et qui les traite ?",
      blocks: [["p", "Bouton **Liste Audit**, à gauche d'Audit dans la barre du haut (le chiffre = observations ouvertes). Tout le monde les lit ; "
        + "les administrateurs les planifient dans une révision, nomment un responsable et répondent. La vue « Plan de révisions » montre ce qui est prévu pour chaque version."]] },

    { q: "Le bouton Audit ne capture pas la page : pourquoi ?",
      blocks: [["p", "Le navigateur n'autorise la capture automatique qu'en HTTPS (ou sur le poste lui-même). Sinon, prenez la capture vous-même (Win+Maj+S), cliquez dans la zone de la fenêtre Audit et collez (Ctrl+V), ou glissez un fichier image."]] },

    { q: "Pourquoi le numéro Generator ne correspond pas à l'heure de ma montre ?",
      blocks: [["p", "Le numéro est la date-heure série Excel en **UTC** (comme l'outil d'origine) : en été, la partie « date » change à 20 h, heure de Montréal. C'est le serveur qui donne le numéro final au moment de la réservation, unique sur toute la plateforme."]] },

    { q: "La recherche ne trouve pas mon texte.",
      blocks: [["list", [
        "Tous les mots doivent apparaître : essayez moins de mots, ou un mot plus court (2 lettres minimum).",
        "Elle cherche dans tous vos Spaces : pages et commentaires, tickets et commentaires, requirements, needs, PR / ECN, questions client, tâches, idées, analyses, références, personnes, Audit. Les feuilles de temps (privées) ne sont pas couvertes.",
        "« ⚙ Recherche avancée » : choisissez les Spaces et les types de résultats, titres seulement, dates, éléments ouverts seulement ; \"phrase exacte\" et -mot pour exclure.",
        "Les accents et majuscules sont ignorés : « etancheite » trouve « Étanchéité »."]]] },

    { q: "Quelle est la différence entre Goldmine, Agile et Exploration ?",
      blocks: [["table", ["Outil", "Question à laquelle il répond", "Grain"], [
        ["Goldmine", "Que doit faire le produit ?", "Un requirement vérifiable"],
        ["Exploration", "Quand, dans les grandes lignes ?", "Des phases et des semaines"],
        ["Agile", "Qui fait quoi, maintenant ?", "Un ticket, un sprint"]]]] },

    { q: "Quel code de temps choisir pour une séance de travail ?",
      blocks: [["p", "L'étape du PDP sur laquelle vous avez travaillé : A-01 à A-06 (pré-étude), B-07 à B-12 (étude conceptuelle : besoins, fonctions, CdCF, concepts), C-13 à C-15 (conception), D-FAB et D-19 à D-21 (fabrication et validation du prototype)."]] },

    { q: "Peut-on empêcher les captures d'écran de la plateforme ?",
      blocks: [["p", "Pas complètement, et aucun site web ne le peut : Impr. écran, l'Outil Capture de Windows ou une photo du "
        + "moniteur échappent au navigateur. Un administrateur peut activer (Admin → Confidentialité) un **filigrane "
        + "nominatif** (votre nom, la date et l'adresse IP sur chaque écran : une capture désigne sa source), le **blocage de "
        + "l'impression**, le **blocage copier / clic droit** et le **flou quand la fenêtre perd le focus**. Chaque tentative "
        + "est journalisée. Le blocage réel des captures relève des postes de travail (stratégies TI)."]] },

    { q: "Que se passe-t-il quand un Space est supprimé ?",
      blocks: [["p", "Un Space doit d'abord être **archivé** ; l'administrateur voit ensuite ce qui sera supprimé et tape la clé "
        + "du Space pour confirmer. Une **sauvegarde complète** est créée juste avant (Admin → Update et sauvegardes → Données) : "
        + "le Space peut être restauré, sous la même clé ou une autre."]] },

    { q: "Une mise à jour a mal tourné, ou des données ont été effacées par erreur : comment revenir en arrière ?",
      blocks: [["p", "Administrateurs : Admin → **Update et sauvegardes** → **↺ Restaurer**. Deux filets, trois chances chacun : "
        + "les **3 dernières versions du code** (« Revenir à la v… », les données ne bougent pas) et les **3 derniers points de "
        + "restauration des données**, pris tout seuls avant chaque mise à jour, import ou configuration, et une fois par jour."],
        ["list", [
          "Une erreur dans un Space : « Récupérer un Space… » → le Space revient tel qu'il était, dans un **nouveau** Space ; recopiez ce qu'il faut.",
          "Une erreur partout : « Revenir à ce point… » → tout le site revient à ce moment (un point « avant retour » est pris d'abord, le journal d'audit est gardé, tout le monde se reconnecte).",
          "Avant une manipulation risquée : « Créer un point maintenant »."]]] },

    { q: "Comment prouver ce qui est sorti vers un client à une date précise (révision de référence) ?",
      blocks: [
        ["p", "Un administrateur **fige une révision** (menu à votre nom → Révisions, ou ⚙ Admin → Révisions) : une copie exacte "
          + "de toute la base, numérotée **revX.XX** et datée, gardée pour toujours sur le serveur (data/baselines/). Le numéro "
          + "monte toujours : +1 par défaut (rev1.10 → rev2.00), ou à la main pour une revue partielle (rev1.15, et rev1.1 = rev1.10)."],
        ["steps", [
          "Révisions → « Consulter » la révision voulue : tout le site s'affiche tel qu'il était, en **lecture seule** (bandeau orange).",
          "Exportez comme d'habitude (Word, Excel, CSV, PDF) : le fichier s'appelle …_rev1.10.docx et porte dans son en-tête (Word) "
            + "ou sa feuille « Révision » (Excel) la révision, sa date, votre nom, vos initiales et le numéro d'extraction.",
          "« Revenir à la base courante » dans le bandeau. Un export fait hors révision porte « hors-rev-<date> » dans son nom.",
          "Le **registre des extractions** (administrateurs) garde chaque fichier sorti : qui, quand, de quelle révision, son empreinte "
            + "SHA-256 ; « Vérifier » contrôle qu'une révision n'a pas été touchée."]],
        ["tip", "Une révision pèse quelques Mo (base compressée ; les pièces jointes ne sont pas recopiées, elles ne changent jamais). "
          + "Les droits appliqués en consultation sont ceux d'aujourd'hui."]] },

    { q: "Est-ce que HeadLamp [Sandbox] compte pour de vrai ?",
      blocks: [["p", "Non : HeadLamp [Sandbox] est un **bac à sable**. Créez, modifiez, cassez : rien n'y touche aux vrais Spaces. Ses requirements et références sont des exemples ; il est fermé aux feuilles de temps."]] },

    { q: "Le thème n'a pas changé : où le choisir ?",
      blocks: [["p", "Menu à votre nom (en haut à droite) → section **Thème** : Thème par défaut ou Terminal R&D, un clic. Les autres "
        + "thèmes (Atlassian, Système, Clair, Sombre, Contraste élevé) sont dans menu à votre nom → Paramètres. Le choix est "
        + "gardé sur le serveur : il vous suit sur tous vos postes."]] },

    { q: "Je ne trouve pas mes @mentions.",
      blocks: [["p", "Dashboard → **Messages** : « Reçus » (ce qu'on vous a écrit) et « Envoyés » (ce que vous avez écrit, avec Lu / "
        + "Non lu). Une mention n'est envoyée que si la personne a accès au Space ; seules les mentions ajoutées par une nouvelle "
        + "version sont envoyées (réenregistrer une page ne renvoie pas les anciennes)."]] },

    { q: "Comment partager le serveur de développement avec un collègue ?",
      blocks: [
        ["steps", [
          "Lancez **Lancer_dev_reseau.bat** (ou lancer_dev.py, MODE = \"reseau\", F5 dans Spyder) : la fenêtre donne l'adresse https:// à transmettre.",
          "Envoyez au collègue le fichier **data/tls/ca.crt** ; il l'installe une fois (double-clic → Installer le certificat → Utilisateur actuel → Autorités de certification racines de confiance). Sur votre poste : python lancer_dev.py reseau --confiance.",
          "Créez-lui un compte (Admin → Utilisateurs) : admin / admin ne s'ouvre que sur votre poste."]],
        ["warn", "C'est un partage de développement : HTTPS avec une CA de développement, réseaux privés seulement. Le collègue ne voit rien ? Le pare-feu Windows bloque Python : la règle demande des droits administrateur. La production, c'est deploy/TLS.md."]] },

    { q: "Mes données sortent-elles de notre serveur ?",
      blocks: [["p", "Non. L'outil tourne sur le serveur de l'équipe, sans CDN, sans police ou service externe ; la page elle-même interdit au navigateur de contacter un autre site, et l'échange est chiffré en HTTPS (TLS 1.3) sur le réseau. Seul ce que **vous** copiez vers un outil externe en sort : d'où la règle sur les agents IA."]] },

    { q: "Pourquoi Goldmine, Dynamite, Exploration… ? Les noms de la mine", newTag: "0.60.02-faq-mine",
      blocks: [
        ["p", "Concevoir un produit, c'est exploiter un gisement : on prospecte, on dégage la roche, on extrait ce qui a de la valeur, on en vérifie la teneur. Chaque module porte le nom de son geste."],
        ["table", ["Module", "Dans la mine", "Dans le projet"], [
          ["Exploration", "La prospection : où creuser, dans quel ordre", "Le plan : phases, jalons, Gantt"],
          ["Goldmine", "Le filon d'or, trié pépite par pépite", "Besoins et requirements « en or », tracés jusqu'à leur essai"],
          ["Diamond 💎", "Le diamant, à 1 000 m : la pierre la plus dure, taillée facette par facette", "Analyse fonctionnelle : arbre des fonctions, puis structure fonctionnelle, risques et DFMEA"],
          ["Dynamite", "La charge qui fait sauter la roche : on dynamite le savoir brut", "Le wiki : notes, procédures, décisions"],
          ["Agile", "Les équipes de forage, par quarts", "Backlog, sprints, Board, Change Management"],
          ["Testing", "L'essai du minerai : mesurer la teneur", "Test Base, procédures et plans d'essai"],
          ["Tools et Generator", "La boîte à outils et le poinçon des lots", "Méthodes de conception, numéros de documents"],
          ["Timesheet", "Le carnet de quart", "Heures par étape du PDP, vacances, réclamations"],
          ["Training, Help & HeadLamp", "L'école de la mine et la HeadLamp qui éclaire la galerie", "Formation, tour du site, bac à sable"]]]] }
  ];
})();
