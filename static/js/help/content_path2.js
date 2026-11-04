/* Help - second half of the path (« tour du site » 0.47.0, D-B-092): Testing, Tools, Training, Timesheet, Recherche
   et Audit, Admin. Same block format as content_path.js; appended in order. */
(function () {
  "use strict";

  const HELP = (DA.help = DA.help || {});
  HELP.path = (HELP.path || []).concat([
    { id: "testing", isNew: true, title: "Testing : tests, procédures et Test Plans", tool: "Testing",
      summary: "La Test Base, les procédures, les plans pour un fournisseur, les listes centrales.",
      blocks: [
        ["p", "**Testing** (après Dynamite) : tous les tests possibles d'un produit grand public mécatronique, par sujet — performance fonctionnelle, sécurité électrique, CEM, thermique, environnement, indice de protection (IP), mécanique et chute, durée de vie, matériaux (RoHS), électronique et logiciel, ergonomie, production, vérification sans test."],
        ["tip", "Une **Test Base par Space** : TESTING est le catalogue de référence ; chaque Space en reçoit sa propre copie à sa première ouverture (Testing → Space), modifiable sans toucher les autres. Les requirements d'un Space citent les tests de sa propre base ; les listes centrales et les procédures (wiki TESTING) restent communes. La liste déroulante en haut de la marge gauche, comme dans Goldmine et Dynamite, dit toujours dans quel Space vous êtes et change de Space en gardant la même vue."],
        ["steps", [
          "**Test Base** : filtrez (texte, Subject, standard, category **Standard** / **Industry Practice** / **Custom Test**, status, niveau, méthode, cité ou non par un requirement). « Exporter la sélection » n'envoie que les lignes affichées ; « Importer (CSV) » montre un aperçu avant d'écrire.",
          "La fiche d'un test : objectif, acceptance criteria, moyens, **source** (standard et section), **lieu**, **équipements**, **fonctions**, sa **procédure** (page du wiki TESTING) et **les requirements qui la citent** dans tous vos Spaces. « Nouveau Test » : l'identifiant suit le sujet (TST-CUS-23…), il démarre en Draft.",
          "**Test Plans** (fournisseurs externes) : cochez des tests dans la Test Base, « Créer un plan de test avec la sélection », choisissez le fournisseur (liste Test Location). « Générer le plan (.docx) » reprend les procédures et les fiches ; le reste est marqué « À COMPLÉTER ». Cycle : Draft → Sent to Supplier → Results Received (« Joindre les résultats (PDF) », obligatoire) → Closed.",
          "**Exporter en Word (.docx)** : les tests affichés deviennent une spécification de tests au gabarit Word, regroupés par sujet, fonction ou lieu."]],
        ["h", "Les listes centrales"],
        ["p", "Testing → Listes : Test Equipment, Test Locations, Product Functions, Acronyms, Definitions. Jamais de texte libre : seul un Admin du Space TESTING ajoute, renomme ou désactive une entrée ; une entrée utilisée n'est jamais effacée."],
        ["tip", "Les standards sont cités par leur titre et leurs sections, jamais reproduits ; les numéros de section sont à vérifier sur l'exemplaire de l'équipe."]] },

    { id: "generator", title: "Tools : Design et Generator", tool: "Tools",
      summary: "Méthodes de conception et références de documents.",
      blocks: [
        ["table", ["Section", "Pour", "Contenu"], [
          ["Design", "Concevoir et décider en équipe", "Brainstorming, brainwriting 6-3-5 en paires tournantes, storytelling, mind map, Pugh matrix, Kepner-Tregoe ; chaque méthode a sa page et sa FAQ (Space TOOLS)"],
          ["Generator", "Nommer et classer un document", "Numéro unique, nom de fichier et dossier selon les livrables du PDP (MIP, RCS, CdCF, RC, RVE)"]]],
        ["h", "Generator, pas à pas"],
        ["steps", [
          "Tools → Generator → Space → « Générer » : type de document, rangé par phase du PDP (A. Pré-étude : MIP… ; B. Étude conceptuelle : RCS, AF, CdCF, Pugh… ; C. Conception : RC, AMDEC… ; D. Fabrication et validation : RVE, protocole et résultats d'essai), puis ingénierie générale ; et l'étape du PDP (09 = recherche des fonctions, 11 = CdCF…). Le titre prend le nom du type (ex. « Cahier des charges fonctionnel ») tant que vous ne l'avez pas modifié.",
          "Le **Project ID** est le nom du Space en majuscules (un seul mot ; sinon sa clé) : il termine le titre. Changez subdivision, code système (optionnel, ex. CHAUF), révision, titre ou Project ID au besoin : l'aperçu se met à jour.",
          "« Réserver la référence » : le **serveur** donne le numéro final, unique sur toute la plateforme.",
          "« Copier le nom », juste à droite du nom de fichier complet, puis collez-le dans le champ Nom de fichier de Word (Enregistrer sous) ; copiez aussi le dossier et enregistrez le document à cet endroit.",
          "« Registre » : toutes les références du Space, nouvelle révision, export CSV. Un numéro n'est jamais réutilisé (annulé, jamais supprimé)."]],
        ["p", "Format : TYPE-DDDDD-TTTTT_RÉV_SYSTÈME Titre Project ID — date-heure série Excel en UTC. Ex. CDCF-46297-60489_1_CHAUF Cahier des charges fonctionnel EQP."]] },

    { id: "training", isNew: true, title: "Training : votre plan de formation", tool: "Training",
      summary: "Topics, plan de l'année, tests avec reprise des questions manquées, évaluation du gestionnaire.",
      blocks: [
        ["steps", [
          "Training → **Topics** : les sujets de formation — un par étape de ce guide (HL-01 à HL-14), la Base de connaissances (KB), "
            + "les méthodes et outils de Tools (TL), le suivi personnel (RH : objectifs, évaluation, profil, Mon équipe) — avec leur "
            + "contenu, leur référence (page wiki ou chapitre Help) et leur test. Vos topics de l'année y portent leur status.",
          "Training → **Mon plan** : choisissez l'année, « Ajouter un topic au plan… ». Chaque item avance To Do → In Progress → "
            + "Completed → Achieved.",
          "« **Passer le test** » : une quinzaine de questions à choix multiples, corrigées par le serveur (les réponses ne sont "
            + "jamais envoyées au navigateur). Votre **note** s'affiche à la fin.",
          "**Sous 80 %**, les questions manquées — et seulement elles — **reviennent**, réponses mélangées, jusqu'à ce que chacune "
            + "soit réussie. Les bonnes réponses ne sont pas montrées avant : relisez la référence entre deux reprises. Vous "
            + "pouvez arrêter et reprendre plus tard (« Reprendre les n question(s) manquée(s) » sur l'item).",
          "Test réussi (directement ou après les reprises) : l'item passe tout seul à **Completed, en vert**. Un topic qui a un "
            + "test ne se marque pas complété à la main.",
          "Votre **gestionnaire** (menu à votre nom → Paramètres) voit votre plan et votre note (« Plan · <nom> »), écrit son "
            + "évaluation et passe l'item à **Achieved** (vert plein).",
          "L'évaluation de l'année se fait dans « Mes objectifs » (lien dans le panneau de gauche) : les topics du plan de formation y sont commentés à mi-année et reçoivent un verdict en fin d'année, comme les objectifs."]],
        ["tip", "Administrateurs et Admin du Space TRAINING : ⚙ Admin → « Gérer les topics et les tests » (test écrit en Markdown, « Partir de l'exemple », 10 à 20 questions, seuil « pass: 80 ») et « Workflow » (qui peut faire chaque passage). Un test modifié pendant une reprise la remet à zéro."]] },

    { id: "timesheet", title: "Timesheet : déclarer ses heures", tool: "Timesheet",
      summary: "Feuille hebdomadaire, codes du PDP, descriptions obligatoires, copies, vacances, approbation, réclamations.",
      blocks: [
        ["steps", [
          "Timesheet → « Ma semaine » : « + Ajouter une plage » puis jour, Space, code de temps (l'étape du PDP : A-01 … D-21), heures (par quarts d'heure).",
          "Écrivez une **courte description** du travail : sans elle, la semaine ne se soumet pas (lignes en rouge).",
          "« Soumettre la semaine » ; tant qu'elle n'est pas approuvée, « Retirer la soumission » la rend modifiable. Elle est approuvée par **votre approbateur** (l'enseignant, un chef d'équipe ou un gestionnaire : menu à votre nom → Paramètres).",
          "Renvoyée ? La note s'affiche : corrigez, soumettez de nouveau."]],
        ["h", "Gagner du temps : copier"],
        ["list", [
          "**⧉ Copier la journée** : recopie toutes les plages d'un jour vers d'autres jours (bouton « Lundi à vendredi »). **⧉** au bout d'une ligne : cette seule plage.",
          "**⧉ Copier une semaine passée…** : reprend une semaine précédente jour pour jour, en ajoutant ou en remplaçant.",
          "Une copie qui ferait dépasser 24 h dans une journée est refusée."]],
        ["h", "Vacances et congé santé"],
        ["list", [
          "Banque de vacances : menu à votre nom → Paramètres (heures restantes et date du solde) ; l'approbateur la voit en approuvant.",
          "Space **INT** (ouvert à tous) : **INT-VAC · Vacances** est déduit de votre banque ; **INT-SAN · Congé santé** (sous approbation) ne l'est jamais. Ni l'un ni l'autre n'est réclamé à un organisme. Principes : INT → Dynamite → « Politiques de l'équipe »."]],
        ["h", "Réclamations et rapports (administrateurs)"],
        ["list", [
          "**Projet financé** (subvention, crédit d'impôt, contrat client) : dans **Spaces et organismes**, créez un **Funding Space** avec ses **Budget Lines** (réclamables ou non, importables d'Excel), puis rattachez-y le Space du projet avec l'organisme et le numéro de contrat. L'équipe saisit ses heures sur ces Budget Lines.",
          "**⚙ Admin → Export et rapport Word** : période, organisme, status des semaines, Budget Lines et Spaces cochés (« x ») ; classeur Excel (Sommaire, Budget Lines avec chaque plage et sa justification, Détail, Lisez-moi) ou **rapport Word** au destinataire (organisme de subvention ou client) avec la justification de chaque heure et l'attestation à signer — sans rien retaper."]],
        ["tip", "Un code par étape du PDP : la feuille de temps de l'équipe montre où le temps a été passé, phase par phase (A. Pré-étude … D. Fabrication et validation)."]] },

    { id: "recherche-audit", title: "Recherche, palette et Audit", tool: "Barre du haut",
      summary: "Retrouver n'importe quoi, y aller au clavier, signaler ce qui cloche.",
      blocks: [
        ["p", "**Recherche** (barre du haut) : partout où vous avez accès — pages et commentaires, tickets, requirements, needs, tests, PR / ECN, questions client, tâches, idées et analyses Tools, références, personnes, Audit. Les meilleurs résultats s'affichent pendant la frappe ; Entrée ouvre la page complète. Tous les mots doivent apparaître (accents et majuscules ignorés) ; \"phrase exacte\", -mot pour exclure. **⚙ Recherche avancée** : Spaces, types, titres seulement, dates, éléments ouverts seulement."],
        ["p", "**Palette (Ctrl+K)** : pour **aller** quelque part (onglet, Space, écran d'Admin) plutôt que chercher un contenu. Les mots se tapent dans n'importe quel ordre ; ↑ ↓ puis Entrée, Échap pour fermer."],
        ["p", "**Audit** : sur l'écran qui pose problème, cliquez « Audit ». La page est capturée (ou collez une capture : Win+Maj+S puis Ctrl+V), décrivez le problème ou l'amélioration, envoyez."],
        ["p", "**Liste Audit** (avec le nombre d'observations ouvertes) : toutes les observations, filtrables et triables ; la vue **Plan de révisions** montre une colonne par révision cible."],
        ["tip", "Administrateurs : cochez plusieurs lignes puis « Planifier dans cette révision » ; donnez un responsable, répondez dans « Réponse / suivi », « Exporter CSV » pour préparer une révision."]] },

    { id: "administration", title: "Admin (administrateurs)", tool: "Admin",
      summary: "Comptes, Spaces, plateforme, mise à jour du code, sécurité réseau, partage en développement.",
      blocks: [
        ["p", "Onglet **⚙ Admin**, tout à droite : administrateurs seulement. Trois groupes : **Comptes** (Utilisateurs, Droits, Règles d'accès), **Spaces** (Spaces, Setup des Spaces) et **Plateforme** (Update et sauvegardes, Sécurité réseau, Confidentialité, Journal d'audit). Dans chaque module, les réglages sont sous « ⚙ Admin » dans la marge gauche."],
        ["list", [
          "**Utilisateurs** : créer, désactiver, mot de passe temporaire, « Profil… » (profil d'études), « Dupliquer… » (mêmes droits qu'un profil existant), « Feuille de temps… » (approbateur, banque de vacances).",
          "**Droits** : la grille comptes × Spaces (Lecteur, Éditeur, Admin du Space). **Règles d'accès** : comptes et droits en texte, vérification à blanc avant d'appliquer.",
          "**Spaces** : créer (prêt dans chaque onglet), archiver → sauvegarder → supprimer (après confirmation par la clé, sauvegarde automatique juste avant). **Setup des Spaces** : tous les écrans de configuration au même endroit.",
          "**Update et sauvegardes** : un seul onglet, cinq volets, et l'encadré « Que voulez-vous faire ? » qui mène au bon. **↺ Restaurer** : les 2 × 3 chances, soit les 3 dernières versions du code (« Revenir à la v… ») et les 3 derniers points de restauration des données (« Récupérer un Space… » dans un nouveau Space, ou « Revenir à ce point… » pour tout le site). **Framework** : exporter le code pour Claude, vérifier puis appliquer le zip rendu. **Configuration** : tous les réglages en .md, aperçu des différences, versions gardées 3 mois. **Données** : paquets scellés (comptes et Spaces) et sauvegardes .zip de chaque Space (restaurées toujours dans un nouveau Space). **Site complet** : déménager le site. Guide : BDC → « Mettre à jour le site ».",
          "**Révisions** (Plateforme, et menu à votre nom → Révisions pour tous) : « Figer une révision » copie toute la base, datée, à votre nom, en **revX.XX** (vide = +1 : rev1.10 → rev2.00 ; à la main, toujours plus grand, rev1.1 = rev1.10 ; jamais en arrière). « Consulter » montre tout le site tel qu'il était, en lecture seule (bandeau orange), avec les droits d'aujourd'hui ; chaque Word / Excel / CSV / PDF exporté porte alors la révision dans son nom (…_rev1.10.docx) et dans son en-tête, avec la personne et la date. Hors révision, le nom porte « hors-rev-<date> ». Le **registre des extractions** dit qui a sorti quoi, de quelle révision, quand. Fichiers : data/baselines/ (quelques Mo par révision, jamais effacés).",
          "**Sécurité réseau** : ce qui protège l'échange navigateur ↔ serveur (HTTPS TLS 1.3, certificat et expiration, mTLS, HSTS) et les couches réseau. Guide : deploy/TLS.md.",
          "**Confidentialité** : filigrane nominatif, blocage de l'impression, du copier / clic droit, flou hors focus ; chaque tentative est journalisée.",
          "**Journal d'audit** : qui a fait quoi, quand."]],
        ["h", "Développement : partager le serveur avec un collègue"],
        ["steps", [
          "Sur le poste qui fait tourner la plateforme : double-clic sur **Lancer_dev_reseau.bat** (ou, dans Spyder, lancer_dev.py avec MODE = \"reseau\", F5).",
          "La fenêtre affiche l'adresse à donner au collègue (ex. https://192.168.1.23:8443) et le fichier **data/tls/ca.crt** à lui envoyer : il l'installe (double-clic → Installer le certificat → Utilisateur actuel → Autorités de certification racines de confiance) ; sinon son navigateur avertit.",
          "Créez-lui un compte : Admin → Utilisateurs (mot de passe temporaire « admin » en développement, à changer à la première connexion). Le compte admin / admin ne s'ouvre que sur votre poste.",
          "Seuls les réseaux privés (et le sous-réseau de votre poste) entrent ; pour un seul collègue : COLLEGUES = [\"192.168.1.40\"] dans lancer_dev.py."]],
        ["warn", "Le pare-feu Windows doit autoriser Python sur les réseaux privés ; sans droits administrateur, demandez la règle à l'IT. Ce mode n'est **pas** la production : en service, c'est votre serveur avec un vrai certificat (deploy/TLS.md)."]] },
  ]);
})();
