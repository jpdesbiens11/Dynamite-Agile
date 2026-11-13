/* Dynamite | Agile - application shell: login, navigation, home, about. */
(function () {
  "use strict";

  const { api, el, clear, field, roleBadge, toast, modal, initials } = DA;
  const root = document.getElementById("app");
  const session = {
    user: null,
    projects: [],
    about: { name: "Dynamite | Agile", version: "", description: "" },
  };
  DA.session = session;

  DA.onUnauthorized = function () {
    if (!session.user) return;
    session.user = null;
    DA.setCsrf(null);
    DA.applyPolicy({}, null);
    showLogin("Votre session a expiré. Reconnectez-vous.");
  };

  /* D-B-052: « hide the sandbox » setting -- the DEMO space disappears everywhere except in
     Dynamite (its wiki is the users' help) and Help. */
  const SANDBOX_KEY = "DEMO";
  const WIKI_ONLY_KEY = "TOOLS";  // D-B-068: the Tools wiki shows only in Dynamite (reached from the Tools tab)
  function visibleProjects(view) {
    const all = (session.allProjects || []).filter((p) => p.key !== WIKI_ONLY_KEY || view === "dynamite");
    if (!(session.prefs && session.prefs.hide_sandbox) || view === "dynamite" || view === "help") return all;
    return all.filter((p) => p.key !== SANDBOX_KEY);
  }
  DA.sandboxHidden = (view) => !!(session.prefs && session.prefs.hide_sandbox) && view !== "dynamite" && view !== "help";
  DA.sandboxKey = SANDBOX_KEY;
  DA.wikiOnlyKey = WIKI_ONLY_KEY;  // 0.60.19: never offered as the default Space (it opens in Dynamite only)

  function applyMe(me) {
    session.user = me.user;
    session.allProjects = me.projects || [];
    session.projects = visibleProjects("");
    session.modules = me.modules || [];
    session.prefs = me.prefs || {};
    session.team = me.team || { size: 0, pending: 0 };  // D-B-112: « Mon équipe »
    DA.setCsrf(me.csrf);
    /* Core lot v0.10: personal settings (D-B-028) and content protection (D-B-029). */
    DA.applyPrefs(session.prefs);
    DA.applyPolicy(me.policy, me.user, me.client_ip);
    if (DA.initialsChanged) DA.initialsChanged();  // D-B-058 banner
  }

  /* 0.60.01: the logo is the name of the tool, in text (top bar and login screen) -- no image to replace when
     an installation customises its look: change the --dynamite / --agile colours. */
  function companyBrand(onDark) {
    return el("span", { class: "da-logo" + (onDark ? " da-logo-top" : "") }, el("img", { class: "brand-mark", src: "/favicon.svg", alt: "" }), brand());
  }

  /* Software name, kept for the About dialog. */
  function brand() {
    return el("span", { class: "brand", role: "img", "aria-label": "Dynamite Agile" },  // 0.60.32: one word, two colours
      el("span", { class: "brand-dynamite" }, "Dynamite"), el("span", { class: "brand-agile" }, "Agile"));
  }

  function closeMenus() {
    document.querySelectorAll(".menu").forEach((menu) => { menu.hidden = true; });
  }

  /* ---------------- Login ---------------- */
  function showLogin(message) {
    clear(root);
    const username = el("input", { type: "text", autocomplete: "username", required: true, maxlength: 64 });
    const password = el("input", { type: "password", autocomplete: "current-password", required: true });
    const error = el("p", { class: "form-error", role: "alert" }, message || "");
    const submit = el("button", { type: "submit", class: "btn btn-primary btn-block" }, "Se connecter");

    const form = el("form", {
      class: "auth-card",
      onsubmit: async (ev) => {
        ev.preventDefault();
        error.textContent = "";
        submit.disabled = true;
        try {
          applyMe(await api.post("/api/login", { username: username.value.trim(), password: password.value }));
          password.value = "";
          if (DA.bootSequence) await DA.bootSequence(session);  // D-B-088: « Terminal R&D » boot log (skippable)
          route();
        } catch (err) {
          error.textContent = err.message;
          password.value = "";
          password.focus();
        } finally {
          submit.disabled = false;
        }
      },
    },
      companyBrand(),
      el("h1", { class: "auth-title" }, "Connexion"),
      field("Identifiant", username),
      field("Mot de passe", DA.passwordToggle(password)),  // 0.60.96 (D-O-102): eye button
      error,
      submit,
      el("p", { class: "auth-note" }, "Atelier de conception de produit : besoins, fonctions, requirements, essais."),
      el("p", { class: "auth-note" }, el("a", { href: "/apps/vitrine/index.html", target: "_blank", rel: "noopener" },
        "Nouveau ? Découvrez la plateforme en 3 minutes")));  // D-B-087: the showcase page
    const guestEntry = DA.guestEntry(session.about, async (me) => { applyMe(me); route(); });  // 0.60.63 (D-O-072)
    if (guestEntry) submit.after(guestEntry);
    const forgot = DA.forgotLink && DA.forgotLink(session.about);  // 0.60.73 (D-O-079): « Mot de passe oublié ? »
    if (forgot) submit.after(forgot);

    /* D-B-087: the sign-in page shows the notebook sketch being drawn (default theme) */
    const hero = el("section", { class: "sk-hero", "aria-hidden": "true" },
      el("p", { class: "sk-hero-title" }, "Concevoir un produit, ", el("mark", null, "une fonction"), " à la fois."),
      el("p", { class: "sk-hero-sub" }, "Needs, fonctions, requirements, plan, sprints, wiki, essais et heures : un seul carnet pour toute l'équipe."),
      el("img", { src: "/img/sketch/hero.svg", alt: "" }));
    root.append(el("main", { class: "auth-page sk-auth" }, hero, form));
    if (session.about.dev_mode && !session.about.prefill) {
      // D-B-091: development server shared on the local network, seen from another computer
      form.append(el("p", { class: "auth-note auth-dev", "data-new": "0.47.0-lan-share" }, "Serveur de développement partagé : "
        + "connectez-vous avec le compte que l'on vous a créé (mot de passe temporaire à changer)."));
      username.focus();
    } else if (session.about.dev_mode) {
      // Development phase only (dev_mode in data/config.json), on the computer that runs the server.
      username.value = "admin";
      password.value = "admin";
      form.append(el("p", { class: "auth-note auth-dev" }, "Mode développement : admin / admin pré-rempli."));
      submit.focus();
    } else {
      username.focus();
    }
  }

  /* ---------------- Password change ---------------- */
  function passwordForm(onDone) {
    const current = el("input", { type: "password", autocomplete: "current-password", required: true });
    const next = el("input", { type: "password", autocomplete: "new-password", required: true, minlength: 12 });
    const confirmation = el("input", { type: "password", autocomplete: "new-password", required: true });
    const error = el("p", { class: "form-error", role: "alert" });
    const submit = el("button", { type: "submit", class: "btn btn-primary" }, "Changer le mot de passe");

    return el("form", {
      onsubmit: async (ev) => {
        ev.preventDefault();
        error.textContent = "";
        if (next.value.length < 12) { error.textContent = "Au moins 12 caractères."; return; }
        if (next.value !== confirmation.value) { error.textContent = "Les deux nouveaux mots de passe diffèrent."; return; }
        submit.disabled = true;
        try {
          applyMe(await api.post("/api/me/password", { old_password: current.value, new_password: next.value }));
          toast("Mot de passe changé.", "success");
          onDone();
        } catch (err) {
          error.textContent = err.message;
        } finally {
          submit.disabled = false;
        }
      },
    },
      field("Mot de passe actuel", DA.passwordToggle(current)),
      field("Nouveau mot de passe", DA.passwordToggle(next), "12 caractères minimum, sans votre identifiant."),
      field("Confirmer le nouveau mot de passe", DA.passwordToggle(confirmation)),
      error,
      el("div", { class: "form-actions" }, submit));
  }

  function showForcedPasswordChange() {
    clear(root);
    const form = passwordForm(route);
    const card = el("div", { class: "auth-card" },
      companyBrand(),
      el("h1", { class: "auth-title" }, "Choisissez votre mot de passe"),
      el("p", { class: "muted" }, "Votre mot de passe actuel est temporaire. Remplacez-le pour continuer."),
      form,
      el("p", { class: "auth-note" }, el("button", { type: "button", class: "link-btn", onclick: logout }, "Se déconnecter")));
    root.append(el("main", { class: "auth-page" }, card));
    form.querySelector("input").focus();
  }

  function openPasswordDialog() {
    let close = null;
    close = modal("Changer mon mot de passe", passwordForm(() => close()));
  }

  /* ---------------- Shell ---------------- */
  /* D-B-087: each tab carries its hand-drawn icon and a one-line tooltip (DA.NAV, sketch.js) */
  function navLink(label, href, active, key) {
    const item = DA.NAV && DA.NAV.items[key];
    return el("a", { class: active ? "tab active" : "tab", href, "data-key": key || null, "data-tip": item ? item[1] : null,
      "aria-current": active ? "page" : null }, item ? DA.icon(item[0]) : null, el("span", { class: "tab-label" }, label));
  }

  /* D-B-087: tabs by order of use -- start (Dashboard, Accueil), the engineering chain (needs → plan → work → wiki → tests),
     then the support tools; a module absent from DA.NAV joins the engineering group */
  function orderedTabs(active) {
    const t = DA.t;
    const modules = session.modules.filter((m) => m.placement !== "end" && m.placement !== "tools");
    const tab = (key) => {
      if (key === "dashboard") {  // D-B-032: first; D-A-046: red counter of unread @mentions
        const link = navLink(t("nav.dashboard"), "#/dashboard", active === "dashboard", "dashboard");
        link.classList.add("tab-with-count");
        link.append(el("span", { class: "mention-count", hidden: true, "aria-live": "polite" }));
        return link;
      }
      if (key === "debuter") {  // 0.60.08: the project path, first tab
        const link = navLink(t("nav.debuter"), "#/debuter", active === "debuter", "debuter");
        link.setAttribute("data-new", "0.60.08-debuter");
        return link;
      }
      if (key === "home") return navLink(t("nav.home"), "#/home", active === "home", "home");
      const m = modules.find((x) => x.key === key);
      if (!m) return null;
      return m.available ? navLink(m.label, "#/" + m.key, active === m.key, m.key) : navSoon(m.label, m.phase);
    };
    const groups = (DA.NAV ? DA.NAV.groups : [["dashboard", "home"], modules.map((m) => m.key)]).map((g) => g.slice());
    const listed = new Set(groups.flat());
    modules.filter((m) => !listed.has(m.key)).forEach((m) => groups[Math.min(1, groups.length - 1)].push(m.key));
    const out = [];
    groups.forEach((g, i) => {
      const items = g.map(tab).filter(Boolean);
      items.forEach((n) => n.classList.add(i === 1 ? "tab-core" : "tab-side"));  // D-B-087: the engineering chain keeps its labels longest
      if (!items.length) return;
      if (out.length) out.push(el("span", { class: "tab-group-sep", "aria-hidden": "true" }));
      out.push(...items);
    });
    return out;
  }

  function navSoon(label, step) {
    return el("span", { class: "tab soon", title: "Disponible à l'étape " + step },
      label, el("span", { class: "soon-tag" }, "bientôt"));
  }

  /* « User » (D-B-078): the personal section -- settings, objectives, members of my Spaces. Core lot v0.18
     (D-A-039): Admin is no longer in it -- it has its own tab at the far right of the top bar, administrators only. */
  const USER_VIEWS = ["settings", "objectives", "profile", "team", "members", "revisions"];  // D-B-111 profile, D-B-112 team
  function userNav(active) {
    const user = session.user;
    const t = DA.t;
    const manages = user.is_admin || session.projects.some((p) => p.is_manager);
    const link = (label, href, key) => el("a", { class: "user-section" + (active === key ? " active" : ""), href,
      "aria-current": active === key ? "page" : null }, label);
    return el("nav", { class: "user-sections", "aria-label": "Section User" },
      link(t("menu.settings"), "#/settings", "settings"),
      link(t("menu.objectives"), "#/objectives", "objectives"),
      link("Profil et parcours", "#/profile", "profile"),  // D-B-111
      session.team && session.team.size ? link("Mon équipe", "#/team", "team") : null,  // D-B-112
      manages ? link(t("menu.members"), "#/members", "members") : null, link("Révisions", "#/revisions", "revisions"));
  }

  function menuItem(label, action) {
    return el("button", { type: "button", class: "menu-item", role: "menuitem", onclick: () => { closeMenus(); action(); } }, label);
  }

  function topbar(active) {
    const user = session.user;
    const t = DA.t;
    const manages = user.is_admin || session.projects.some((p) => p.is_manager);
    /* D-A-040: no « User » tab any more -- the blue menu of the signed-in account holds the personal pages. */
    const guest = !!user.is_guest;  // 0.60.63 (D-O-072): a guest has no personal pages and no password
    const menu = el("div", { class: "menu", role: "menu", hidden: true },
      guest ? null : menuItem(t("menu.settings"), () => { location.hash = "#/settings"; }),
      guest ? null : menuItem(t("menu.objectives"), () => { location.hash = "#/objectives"; }),
      menuItem("Training", () => { location.hash = "#/training"; }),  // D-A-045
      session.team && session.team.size ? menuItem(DA.teamLabel(session.team), () => { location.hash = "#/team"; }) : null,  // D-B-112
      manages ? menuItem(t("menu.members"), () => { location.hash = "#/members"; }) : null,
      el("hr"),
      el("hr"),  // 0.60.48 (D-O-057): the themes are in Paramètres only
      guest ? null : menuItem(t("menu.password"), openPasswordDialog),
      guest || !DA.accountMail ? null : menuItem(t("menu.email"), DA.accountMail.open),  // 0.60.73 (D-O-079)
      menuItem(t("menu.about"), showAbout),
      menuItem("Découvrir la plateforme (vitrine)", () => { window.open("/apps/vitrine/index.html", "_blank", "noopener"); }),  // D-B-087
      el("hr"),
      menuItem(t("menu.logout"), logout));
    const trigger = el("button", {
      type: "button", class: "user-button", "aria-haspopup": "menu",
      onclick: (ev) => { ev.stopPropagation(); const wasHidden = menu.hidden; closeMenus(); menu.hidden = !wasHidden; },
    },
      el("span", { class: "avatar", "aria-hidden": "true" }, initials(user.display_name)),
      el("span", { class: "user-name" }, user.display_name),
      el("span", { "aria-hidden": "true" }, "▾"));

    return el("header", { class: "topbar" },
      el("a", { class: "brand-link", href: "#/dashboard", title: "Dynamite | Agile — " + t("dash.title") }, companyBrand(true)),
      el("nav", { class: "tabs", "aria-label": "Navigation principale" }, orderedTabs(active)),
      /* Core lot v0.7 (D-B-022): platform tools. D-B-087: by order of use -- search first, « Mes éléments », then Audit. */
      el("div", { class: "topbar-tools" }, (DA.topbarTools || []).slice().sort((a, b) => (a.order || 50) - (b.order || 50))
        .map((tool) => withIcon(tool(active)))),
      /* Help next to the account, where people look for it (D-B-087; core lot v0.8: its own non-shrinking group). */
      el("nav", { class: "tabs-end", "aria-label": "Aide" },
        session.modules.filter((m) => m.placement === "end" && m.available).map((m) => navLink(m.label, "#/" + m.key, active === m.key, m.key))),
      el("div", { class: "user-area" }, trigger, menu),
      /* Core lot v0.18 (D-A-039): administration functions only (accounts, Spaces, rights, backups, set-up), at the
         far right, for administrators only -- never mixed with the personal « User » tab. */
      user.is_admin ? el("a", { class: "admin-tab" + (active === "admin" ? " active" : ""), href: "#/admin/users",
        "aria-current": active === "admin" ? "page" : null, title: "Administration de la plateforme" },
        DA.icon ? DA.icon("admin") : el("span", { class: "admin-tab-mark", "aria-hidden": "true" }, "⚙"), t("nav.admin")) : null);
  }

  /* D-B-087: hand-drawn icon in front of the Audit tools of the top bar */
  function withIcon(node) {
    if (!node || !DA.icon || !node.classList) return node;
    const name = node.classList.contains("tb-audit-list") ? "auditlist" : node.classList.contains("tb-audit") ? "audit" : null;
    if (name) node.prepend(DA.icon(name));
    const tips = { "tb-audit-list": "Liste Audit : voir et planifier les observations", "tb-audit": "Audit : signaler une correction de cet écran",
      "tb-mine": node.getAttribute("title") || "Mes éléments" };  // state-aware text of prefs.js
    Object.entries(tips).forEach(([cls, tip]) => { if (node.classList.contains(cls)) { node.setAttribute("data-tip", tip); node.removeAttribute("title"); } });
    if (node.classList.contains("tb-mine")) node.prepend(DA.icon("mine"));
    return node;
  }

  /* D-A-044: the left panel of a module or core view (logo, navigation, « ⚙ Admin » group), same look as Agile /
     Goldmine / Timesheet -- resizable and collapsible (sidepanel.js). Returns the page section to render into.
     opts: { mark: "/img/x.png", label, nav: [[href, label, active]], admin: [[href, label, active]] } */
  DA.moduleLayout = function (main, opts) {
    /* the layout rules live in agile.css, normally loaded on entering a module: a core view shown first (the
       Dashboard right after sign-in) loads it itself */
    if (!document.querySelector('link[href="/css/agile.css"]')) document.head.append(el("link", { rel: "stylesheet", href: "/css/agile.css" }));
    clear(main);
    main.classList.add("ag-main");
    const link = ([href, label, active]) => el("a", { class: "ag-nav-item" + (active ? " active" : ""), href,
      "aria-current": active ? "page" : null }, label);
    const admin = session.user && session.user.is_admin && (opts.admin || []).length
      ? el("div", { class: "ag-nav-admin", role: "group", "aria-label": "Admin" },
        el("span", { class: "ag-nav-admin-title" }, "⚙ Admin"), opts.admin.map(link)) : null;
    const page = el("section", { class: "ag-page" });
    main.append(el("div", { class: "ag-layout" },
      el("aside", { class: "ag-sidebar" },
        opts.mark ? el("div", { class: "ag-sidebar-mark" }, el("img", { src: opts.mark, alt: "", class: "gm-mark-img" }))
          : el("div", { class: "ag-sidebar-title" }, opts.label || ""),
        opts.picker || null,  // core lot v0.28 (D-B-103): the Space drop-down, like Goldmine and Dynamite
        el("nav", { class: "ag-nav", "aria-label": "Navigation " + (opts.label || "") }, (opts.nav || []).map(link), admin), opts.footer || null),
      page));
    return page;
  };

  /* Core lot v0.18 (D-A-039): the set-up entries of a module's left panel, in their own « Admin » group shown only
     to an administrator. items: [[view, label]]; returns null for everybody else. */
  DA.adminNav = function (items, active, href) {
    if (!session.user || !session.user.is_admin || !items.length) return null;
    return el("div", { class: "ag-nav-admin", role: "group", "aria-label": "Admin" },
      el("span", { class: "ag-nav-admin-title" }, "⚙ Admin"),
      items.map(([view, label]) => el("a", { class: "ag-nav-item" + (active === view ? " active" : ""), href: href(view),
        "aria-current": active === view ? "page" : null }, label)));
  };

  /* D-B-087: when the tabs do not fit, only the active one keeps its label -- the others show their icon and their
     tooltip (nothing hidden behind a scroll) */
  function fitTabs(bar) {
    const nav = bar.querySelector(".tabs");
    if (!nav) return;
    const over = () => nav.scrollWidth > nav.clientWidth + 2;
    const fit = () => {  // labels everywhere, then tighter, then icons for side groups, then icons except the active tab
      bar.classList.remove("tabs-tight", "tabs-partial", "tabs-compact");
      if (over()) bar.classList.add("tabs-tight");
      if (over()) bar.classList.add("tabs-partial");  // start and support tools: icon only
      if (over()) bar.classList.add("tabs-compact");  // everything but the active tab: icon only
    };
    requestAnimationFrame(fit);
    if (!DA._fitTabsBound) { DA._fitTabsBound = true; window.addEventListener("resize", () => {
      const current = document.querySelector(".topbar");
      if (current) fitTabs(current);
    }); }
  }

  function renderShell(active) {
    clear(root);
    const main = el("main", { class: "content", id: "main" });
    if (DA.setModuleAccent) DA.setModuleAccent(active);  // D-B-087: highlighter colour of the tool
    const bar = topbar(active);
    root.append(bar);
    fitTabs(bar);
    const guestBand = DA.guestBanner && DA.guestBanner(); if (guestBand) root.append(guestBand);  // 0.60.63 (D-O-072)
    if (USER_VIEWS.includes(active)) root.append(userNav(active));  // D-B-078
    const frozen = DA.baselineBanner && DA.baselineBanner(); if (frozen) root.append(frozen);  // D-B-129 revision view
    root.append(main);
    return main;
  }

  /* ---------------- Home ---------------- */
  function renderHome() {
    const main = renderShell("home");
    main.append(el("div", { class: "page-head" },
      el("h1", null, "Mes Spaces"),
      el("p", { class: "muted" }, "Bonjour " + session.user.display_name + ".")));

    if (!session.projects.length) {
      main.append(el("div", { class: "empty" },
        el("h2", null, "Aucun Space pour l'instant"),
        el("p", { class: "muted" }, session.user.is_admin
          ? "Créez un premier Space dans Admin → Spaces (onglet tout à droite)."
          : "Demandez à un administrateur de vous ajouter à un Space."),
        session.user.is_admin
          ? el("a", { class: "btn btn-primary", href: "#/admin/projects" }, "Créer un Space")
          : null));
      return;
    }

    main.append(el("div", { class: "project-list" }, session.projects.map((project) =>
      el("article", { class: "project" },
        el("div", { class: "project-top" }, el("span", { class: "key" }, project.key), roleBadge(project.is_manager ? "manager" : project.role)),
        el("h2", null, project.name),
        el("p", { class: "muted" }, project.description || "Aucune description.")))));
    directory(main);
  }

  /* Who to ask (D-B-016): users with a job title in the access rules. */
  async function directory(main) {
    let people = [];
    try { people = (await api.get("/api/directory")).people; } catch (err) { return; }
    if (!people.length) return;
    main.append(el("section", { class: "home-directory" },
      el("h2", null, "Qui contacter ?"),
      el("p", { class: "muted" }, "Quand une question dépasse une donnée déjà documentée (jugement, décision, "
        + "arbitrage, contexte non écrit). Contact : en personne, sur site."),
      el("div", { class: "directory" }, people.map((p) => el("article", { class: "directory-card" },
        el("h3", null, p.display_name),
        el("p", { class: "dir-title" }, p.title),
        p.expertise ? el("p", null, el("strong", null, "Expertise : "), p.expertise) : null,
        p.route_when ? el("p", null, el("strong", null, "S'adresser à lui quand : "), p.route_when) : null)))));
  }

  /* ---------------- About / logout ---------------- */
  function showAbout() {
    const about = session.about;
    modal("À propos", el("div", { class: "about" },
      brand(),
      el("p", { class: "about-version" }, "Version " + about.version),
      el("p", null, about.description),
      el("p", { class: "muted" }, "Les données restent sur votre serveur. Aucune ressource externe n'est chargée.")));
  }

  async function logout() {
    try { await api.post("/api/logout"); } catch (err) { /* already logged out */ }
    session.user = null; DA.setCsrf(null); DA.applyPolicy({}, null); showLogin();
  }

  /* ---------------- Router ---------------- */
  async function route() {  // 0.60.23: same tab and Space (#/module/KEY): the page stays where it was (scrollkeep.js)
    const hold = DA.placeHold(location.hash);
    try { await routeTo(); } finally {
      DA.releaseScroll(hold);
      if (session.user && session.modules) DA.prefetchModuleAssets(session.modules);  // D-O-107: the other tabs, when idle
    } }
  async function routeTo() {
    closeMenus();
    if (!session.user) { showLogin(); return; }
    if (session.user.must_change_password) { showForcedPasswordChange(); return; }

    const prefs = session.prefs || {};  // 0.60.08: « Débuter » until it is closed, then the chosen landing page (D-B-032)
    const start = "#/" + (prefs.debuter_done === false ? "debuter" : (prefs.landing || "dashboard"));
    const parts = (location.hash && location.hash !== "#/" ? location.hash : start).replace(/^#\/?/, "").split("/");
    if (parts[0] === "user") { location.replace("#/settings"); return; }  // D-B-078
    if (parts[0] === "admin" && session.user.is_admin) {
      await DA.admin.render(renderShell("admin"), parts[1] || "users", parts[2]);  // D-B-105: part of a section
      return;
    }
    try {
      applyMe(await api.get("/api/me"));
    } catch (err) {
      if (err.status === 401) return;  // onUnauthorized already showed the login
      toast(err.message, "error");
    }
    session.projects = visibleProjects(parts[0]);
    if (DA.coreViews && DA.coreViews[parts[0]]) {  // core lot v0.7: #/search, #/audit
      DA.coreViews[parts[0]](renderShell(parts[0]), parts.slice(1));
      return;
    }
    await DA.loadModuleAssets(session.modules, parts[0]);  // 0.60.100 (D-O-107): this module and what it requires
    const mod = session.modules.find((m) => m.key === parts[0] && m.available);
    if (mod && DA.views[mod.key]) {
      await DA.views[mod.key](renderShell(mod.placement === "tools" ? "tools" : mod.key), parts.slice(1));  // D-B-065
      return;
    }
    renderHome();
  }

  async function boot() {
    document.addEventListener("click", closeMenus);
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") closeMenus(); });
    window.addEventListener("hashchange", route);

    try { session.about = await api.get("/api/about"); } catch (err) { /* keep defaults */ }
    const reset = DA.resetToken && DA.resetToken();  // 0.60.73 (D-O-079): the link of « Mot de passe oublié ? »
    if (reset) { await DA.showReset(root, reset, companyBrand, () => showLogin()); return; }
    try {
      applyMe(await api.get("/api/me"));
    } catch (err) {
      showLogin(err.status === 401 ? "" : err.message);
      return;
    }
    route();
  }

  boot();
})();
