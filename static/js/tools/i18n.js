/* Interface language (core lot v0.10, D-B-028): French (reference) and
   English for the shell -- top bar, menus, dashboard, settings, member
   screens. Module screens follow screen by screen in later versions.
   DA.t(key) returns the text of the current language, the French text when
   a key is missing. Loaded first among the platform tools. */
(function () {
  "use strict";

  const TEXT = {
    fr: {
      "nav.debuter": "Débuter", "nav.dashboard": "Dashboard", "nav.home": "Accueil", "nav.admin": "Admin", "nav.user": "User",
      "menu.settings": "Paramètres", "menu.members": "Membres de mes Spaces", "menu.objectives": "Mes objectifs", "menu.password": "Changer mon mot de passe", "menu.email": "Courriel de récupération",
      "menu.admin": "Administration", "menu.about": "À propos", "menu.logout": "Se déconnecter",
      "tools.search": "Rechercher…", "tools.auditList": "Liste Audit", "tools.audit": "Audit",
      "tools.mine": "Mes éléments", "tools.mineOn": "Filtre « Mes éléments » actif : seuls vos tickets et tasks s'affichent. Cliquez pour tout voir.",
      "tools.mineOff": "Afficher seulement mes tickets et tasks, partout (Getting Things Done).",
      "dash.title": "Mon Dashboard", "dash.hello": "Bonjour", "dash.sub": "Tout ce qui vous attend, dans tous vos Spaces.",
      "dash.open": "Ouvrir", "dash.all": "Tout voir", "dash.late": "en retard", "dash.due": "échéance",
      "dash.projects": "Mes Spaces", "dash.none": "Rien à signaler.", "dash.more": "autre(s)",
      "set.title": "Paramètres", "set.sub": "Appliqués tout de suite, sur tous vos postes.",
      "set.display": "Affichage", "set.language": "Langue", "set.theme": "Thème", "set.font": "Police",
      "set.size": "Taille du texte", "set.density": "Densité", "set.landing": "Page d'ouverture",
      "set.work": "Travail", "set.mine": "Filtre « Mes éléments » activé par défaut",
      "set.hr": "Feuille de temps", "set.manager": "Mon approbateur (approuve mes feuilles de temps)",
      "set.managerHelp": "L'enseignant, le chef d'équipe ou le gestionnaire qui approuve vos feuilles de temps.",
      "set.bank": "Banque de vacances (heures restantes)", "set.bankDate": "À la date du",
      "set.bankHelp": "Chaque heure « INT-VAC · Vacances » saisie à partir de cette date est déduite. Votre approbateur voit ce solde en approuvant.",
      "set.saved": "Enregistré.", "set.none": "— personne —",
      "set.initials": "Mes initiales — clé de traçabilité (obligatoire)", "set.initialsHelp": "Données d'office d'après votre nom (JDE pour Jean-Philippe Desbiens, ADM pour admin) ; modifiables : exactement 3 lettres, uniques dans la plateforme. Elles signent chaque modification.",
      "theme.system": "Système (clair ou sombre selon Windows)", "theme.light": "Clair", "theme.dark": "Sombre",
      "theme.carnet": "Thème par défaut (croquis d'ingénieur)", "theme.terminal": "Terminal R&D (labo geek, sombre)", "theme.atlassian": "Atlassian (couleurs Jira / Confluence)", "theme.contrast": "Contraste élevé",
      "font.system": "Segoe UI (système)", "font.atlassian": "Pile système Atlassian", "font.readable": "Grande lisibilité (Verdana)",
      "density.comfortable": "Confortable", "density.compact": "Compacte",
      "landing.dashboard": "Mon Dashboard", "landing.home": "Accueil (mes Spaces)", "landing.debuter": "Débuter (parcours du projet)",
      "mem.title": "Membres du Space", "mem.add": "Ajouter", "mem.role": "Droit", "mem.remove": "Retirer",
    },
    en: {
      "nav.debuter": "Get started", "nav.dashboard": "Dashboard", "nav.home": "Home", "nav.admin": "Admin", "nav.user": "User",
      "menu.settings": "Settings", "menu.members": "My projects' members", "menu.objectives": "My objectives", "menu.password": "Change my password", "menu.email": "Recovery e-mail",
      "menu.admin": "Administration", "menu.about": "About", "menu.logout": "Sign out",
      "tools.search": "Search…", "tools.auditList": "Audit list", "tools.audit": "Audit",
      "tools.mine": "My items", "tools.mineOn": "« My items » filter on: only your tickets and tasks are shown. Click to see everything.",
      "tools.mineOff": "Show only my tickets and tasks, everywhere (Getting Things Done).",
      "dash.title": "My dashboard", "dash.hello": "Hello", "dash.sub": "Everything waiting for you, across all your projects.",
      "dash.open": "Open", "dash.all": "See all", "dash.late": "late", "dash.due": "due",
      "dash.projects": "My projects", "dash.none": "Nothing to report.", "dash.more": "more",
      "set.title": "Settings", "set.sub": "Applied immediately, on all your devices.",
      "set.display": "Display", "set.language": "Language", "set.theme": "Theme", "set.font": "Font",
      "set.size": "Text size", "set.density": "Density", "set.landing": "Start page",
      "set.work": "Work", "set.mine": "« My items » filter on by default",
      "set.hr": "Time sheet", "set.manager": "My approver (approves my time sheets)",
      "set.managerHelp": "The instructor, team lead or manager who approves your time sheets.",
      "set.bank": "Vacation bank (hours left)", "set.bankDate": "As of",
      "set.bankHelp": "Every « INT-VAC · Vacation » hour entered from this date on is deducted. Your approver sees this balance when approving.",
      "set.saved": "Saved.", "set.none": "— nobody —",
      "set.initials": "My initials — traceability key", "set.initialsHelp": "Given from your name (JDE for Jean-Philippe Desbiens, ADM for admin); you can change them: exactly 3 letters, unique on the platform. They sign every change.",
      "theme.system": "System (light or dark as in Windows)", "theme.light": "Light", "theme.dark": "Dark",
      "theme.carnet": "Default theme (engineer sketch)", "theme.terminal": "R&D Terminal (geek lab, dark)", "theme.atlassian": "Atlassian (Jira / Confluence colors)", "theme.contrast": "High contrast",
      "font.system": "Segoe UI (system)", "font.atlassian": "Atlassian system stack", "font.readable": "High readability (Verdana)",
      "density.comfortable": "Comfortable", "density.compact": "Compact",
      "landing.dashboard": "My dashboard", "landing.home": "Home (my projects)", "landing.debuter": "Get started (project path)",
      "mem.title": "Project members", "mem.add": "Add", "mem.role": "Right", "mem.remove": "Remove",
    },
  };

  let lang = "fr";
  DA.setLanguage = function (value) {
    const before = lang;
    lang = TEXT[value] ? value : "fr";
    if (before !== lang) window.dispatchEvent(new CustomEvent("da:language", { detail: lang }));  // 0.60.67: cards that carry their own text
    document.documentElement.lang = lang;
    if (DA.domLanguage) DA.domLanguage(lang);  // 0.60.66 (D-O-073): the display dictionary for the module screens
  };
  DA.lang = () => lang;
  DA.t = (key) => (TEXT[lang] && TEXT[lang][key]) || TEXT.fr[key] || key;
})();
