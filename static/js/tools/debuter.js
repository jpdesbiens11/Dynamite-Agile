/* Dynamite | Agile - « Débuter » #/debuter (0.60.08): how to start a project and what to do, in the order of the PDP, in
   each module. The landing page after sign-in until the person closes it (pref debuter_done), then a tab at the start of
   the top bar. Content in debuter_content.js. */
(function () {
  "use strict";

  const { el, clear, toast } = DA;

  function href(link) {
    const [, hash, view] = link;
    const key = (DA.session.prefs || {}).default_space;
    return view && key ? hash + "/" + key + "/" + view : hash;
  }

  /* Without a default Space, a link to a view opens the same list as its tab: show that tab once (0.60.08). */
  function unique(links) {
    const seen = new Set();
    return links.map((l) => ({ label: l[0], href: href(l) })).filter((l) => !seen.has(l.href) && seen.add(l.href));
  }

  function step(s, isAdmin) {
    const [module, title, text, links, adminOnly] = s;
    const locked = adminOnly && !isAdmin;
    return el("li", { class: "dbt-step" },
      el("span", { class: "dbt-icon", "aria-hidden": "true" }, DA.icon(module)),
      el("div", { class: "dbt-body" },
        el("h3", null, title, adminOnly ? " " : null, adminOnly ? DA.badge("Administrateur", "info") : null),
        el("p", null, text),
        locked ? el("p", { class: "muted" }, "Votre administrateur s'en charge.")
          : el("div", { class: "dbt-links" }, unique(links).map((l, i) => el("a", { class: "btn btn-small" + (i ? "" : " btn-primary"), href: l.href }, l.label)))));
  }

  function phase(p, isAdmin) {
    return el("section", { class: "dbt-phase", id: "dbt-" + p.id },
      el("p", { class: "dbt-kicker" }, p.kicker),
      el("h2", null, p.title),
      el("p", { class: "muted" }, p.text, p.deliverable ? el("span", null, " Livrable : ", el("strong", null, p.deliverable), ".") : null),
      el("ol", { class: "dbt-steps" }, p.steps.map((s) => step(s, isAdmin))));
  }

  function render(main) {
    const isAdmin = !!(DA.session.user && DA.session.user.is_admin);
    const done = !!(DA.session.prefs || {}).debuter_done;
    const toggle = el("button", { type: "button", class: "btn", onclick: async () => {
      try {
        await DA.savePrefs({ debuter_done: !done });
        toast(done ? "« Débuter » s'ouvrira de nouveau à l'arrivée." : "Fermée : vous arriverez désormais sur votre page d'arrivée.", "success");
        if (!done) location.hash = "#/" + ((DA.session.prefs || {}).landing || "dashboard");
        else render(main);
      } catch (err) { toast(err.message, "error"); }
    } }, done ? "Ouvrir « Débuter » à l'arrivée" : "J'ai compris : ne plus l'ouvrir à l'arrivée");
    clear(main);
    main.append(
      el("div", { class: "page-head dbt-head", "data-new": "0.60.08-debuter" },
        el("h1", null, "Débuter"),
        el("p", { class: "muted" }, "Démarrer un projet, puis le mener de la découverte du client au lancement du produit : ce que "
          + "vous faites à chaque phase, et dans quel module. Chaque bouton ouvre l'écran, dans votre Space par défaut."),
        (DA.session.prefs || {}).default_space ? null : el("p", { class: "dbt-hint" }, DA.badge("Conseil", "info"), " Choisissez votre Space par "
          + "défaut dans l'", el("a", { href: "#/home" }, "Accueil"), " : les boutons ouvriront alors directement le bon écran (Q&A, Board…)."),
        el("nav", { class: "dbt-toc", "aria-label": "Phases" }, DA.debuterContent.map((p) =>
          el("a", { href: "#dbt-" + p.id, onclick: (ev) => { ev.preventDefault(); document.getElementById("dbt-" + p.id).scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }); } },
            p.id.length === 1 ? p.id + ". " + p.title : p.title)))),
      DA.debuterTornado(DA.debuterContent.filter((p) => p.mvp)),  // 0.60.09 (D-O-021): one turn per phase
      ...DA.debuterContent.map((p) => phase(p, isAdmin)),
      el("div", { class: "form-actions dbt-foot" }, el("a", { class: "btn", href: "#/help" }, "Guide complet"), toggle));
  }

  DA.coreViews = DA.coreViews || {};
  DA.coreViews.debuter = (main) => render(DA.moduleLayout(main, { mark: DA.mark("help"), label: "Débuter",
    nav: [["#/debuter", "Débuter", true], ["#/help", "Guide", false], ["#/dashboard", "Dashboard", false]] }));
})();
