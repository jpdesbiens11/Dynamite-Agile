/* Personal dashboard #/dashboard (core lot v0.10, D-B-032): first link of the
   top bar, right after the logo, and the default start page. Shows
   what waits for the person across every project he can see: Agile
   tickets, ECN / change requests, Goldmine requirements, Exploration plan
   tasks, time sheet, approvals, Audit observations.

   0.20.0 (D-B-038), both ways of acting, from where the person already is:
   - act here: each item has its link and a « status » menu with the moves
     allowed by its workflow; the change is saved and the dashboard refreshed;
   - go there: « Ouvrir la liste » per project opens the right list (board,
     changes, requirements, plan, Q&A) with « Mes éléments » switched on.
   A KPI tile scrolls to its section. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;

  async function openMine(href) {
    if (!DA.myItems()) {
      try { await DA.savePrefs({ my_items: true }); } catch (err) { toast(err.message, "error"); }
    }
    location.hash = href;
  }

  function kpi(k) {
    return el("a", { class: "db-kpi db-kpi-" + (k.tone || "neutral"), href: "#/dashboard",
      title: "Voir la section", onclick: (ev) => {
        ev.preventDefault();
        const target = document.getElementById("db-" + k.key);
        if (!target) { if (k.href) location.hash = k.href; return; }
        target.scrollIntoView({ block: "start", behavior: "smooth" });
        target.classList.add("db-flash");
        setTimeout(() => target.classList.remove("db-flash"), 1200);
      } },
    el("span", { class: "db-kpi-value" }, String(k.value)),
    el("span", { class: "db-kpi-label" }, k.label),
    k.note ? el("span", { class: "db-kpi-note" }, k.note) : null);
  }

  function statusMenu(it, reload) {
    const a = it.action;
    if (!a || !a.choices || !a.choices.length) return el("span", { class: "db-status" }, it.status || "");
    const sel = el("select", { class: "db-status-sel", "aria-label": "Changer le status de " + it.title, title: "Changer le status" },
      el("option", { value: "", selected: true }, (a.current || it.status || "Status") + " ▾"),
      a.choices.map(([value, label]) => el("option", { value: String(value) }, "→ " + label)));
    sel.addEventListener("change", async () => {
      if (!sel.value) return;
      const label = sel.selectedOptions[0].textContent.replace("→ ", "");
      sel.disabled = true;
      try {
        const body = {};
        body[a.field] = a.field === "transition_id" ? Number(sel.value) : sel.value;
        await (a.method === "PATCH" ? api.patch(a.url, body) : api.post(a.url, body));
        toast(it.title.split(" · ")[0] + " → " + label + ".", "success");
        reload();
      } catch (err) { toast(err.message, "error"); sel.disabled = false; sel.value = ""; }
    });
    return sel;
  }

  function item(it, reload) {
    const meta = [it.project, it.due ? DA.t("dash.due") + " " + it.due : "", it.meta].filter(Boolean).join(" · ");
    return el("li", { class: "db-item" },
      el("a", { href: it.href || "#/dashboard", title: it.title }, it.title),
      it.late ? el("span", { class: "db-late" }, DA.t("dash.late")) : null,
      el("span", { class: "db-item-meta" }, meta),
      statusMenu(it, reload));
  }

  /* One « Ouvrir la liste » link per project of the section. */
  function listLinks(s) {
    if (!s.list_href || !s.items.length) return s.href ? el("a", { href: s.href }, DA.t("dash.all")) : null;
    const counts = {};
    s.items.forEach((it) => { counts[it.project] = (counts[it.project] || 0) + 1; });
    return el("span", { class: "db-open" }, Object.entries(counts).map(([key, n]) =>
      el("a", { href: s.list_href.replace("{key}", key), class: "db-open-link",
        title: s.mine ? "Ouvrir la liste de " + key + " avec « Mes éléments » actif" : "Ouvrir la liste de " + key,
        onclick: (ev) => { ev.preventDefault(); if (s.mine) openMine(s.list_href.replace("{key}", key)); else location.hash = s.list_href.replace("{key}", key); } },
      "Ouvrir " + key + (Object.keys(counts).length > 1 ? " (" + n + ")" : "") + " →")));
  }

  function section(s, reload) {
    const more = s.total > s.items.length ? el("p", { class: "muted" }, "+ " + (s.total - s.items.length) + " " + DA.t("dash.more")) : null;
    return el("section", { class: "db-section", id: "db-" + s.key },
      el("div", { class: "db-section-head" }, el("h2", null, s.title + " (" + s.total + ")"), listLinks(s)),
      s.items.length ? el("ul", { class: "db-items" }, s.items.map((it) => item(it, reload))) : el("p", { class: "muted" }, s.empty || DA.t("dash.none")),
      more);
  }

  let viewAs = "";  // D-B-046: administrators look at an employee's dashboard, read-only
  let showAll = false;  // 0.60.42 (D-O-051): the default Space alone, or every Space

  async function render(main) {
    const y = window.scrollY;
    const first = !main.querySelector(".db-grid");
    if (first) { clear(main); main.append(el("p", { class: "loading" }, "…")); }
    let data;
    const q = [viewAs ? "user=" + viewAs : "", showAll ? "all=1" : ""].filter(Boolean).join("&");
    try { data = await api.get("/api/dashboard" + (q ? "?" + q : "")); } catch (err) { toast(err.message, "error"); viewAs = ""; return; }
    const reload = () => render(main);
    DA.refreshView = reload;
    /* D-A-046: « Messages » (@mentions) at the top left -- personal, so never in the read-only « voir comme » mode */
    const messages = !data.viewing && DA.messagesPanel ? await DA.messagesPanel() : null;
    /* 0.60.07 (D-O-019): « Commencer un projet » put forward for an administrator until a first project is started that way */
    let starter = null;
    if (!data.viewing && DA.session.user && DA.session.user.is_admin) {
      try { starter = (await api.get("/api/starter/status")).show; } catch (err) { starter = null; }
    }
    clear(main);
    let picker = null;
    if (data.people) {
      picker = el("select", { class: "db-viewas", "aria-label": "Voir le Dashboard de" },
        data.people.map((p) => el("option", { value: p.id === data.me ? "" : String(p.id), selected: String(p.id) === String(viewAs || data.me) },
          p.id === data.me ? "Moi (" + p.display_name + ")" : p.display_name)));
      picker.addEventListener("change", () => { viewAs = picker.value; render(main); });
    }
    main.append(el("div", { class: "db-head" },
      el("div", null, el("h1", null, data.viewing ? "Dashboard de " + data.viewing.display_name : DA.t("dash.title")),
        el("p", { class: "muted" }, data.viewing ? "Charge de travail courante, telle que la personne la voit."
          : DA.t("dash.hello") + " " + data.user + ". " + (data.scope && data.scope.space
            ? "Tout ce qui vous attend dans le Space de votre produit." : DA.t("dash.sub")))),
      picker ? el("label", { class: "db-viewas-wrap" }, "Voir le Dashboard de ", picker) : null,
      el("p", { class: "muted db-hint" }, data.viewing ? "" : "Changez un status ici (menu ▾), ou « Ouvrir » la liste filtrée sur vos éléments."),
      data.default_space ? el("p", { class: "db-scope", "data-new": "0.60.42-dash-scope" }, data.scope.space
        ? ["Space ★ ", el("strong", null, data.scope.space), " : tout ce qui vous attend dans ce produit. ",
          el("button", { type: "button", class: "link-btn", onclick: () => { showAll = true; render(main); } }, "Voir tous mes Spaces")]
        : ["Tous vos Spaces. ", el("button", { type: "button", class: "link-btn", onclick: () => { showAll = false; render(main); } },
          "Revenir au Space ★ " + data.default_space)]) : ""),
    data.viewing ? el("p", { class: "db-audit-banner", role: "status" }, el("strong", null, "Mode audit — lecture seule. "),
      "Vous voyez le Dashboard de " + data.viewing.display_name + " ; rien ne peut être modifié ici. La consultation est journalisée. ",
      el("button", { type: "button", class: "link-btn", onclick: () => { viewAs = ""; render(main); } }, "Revenir à mon Dashboard")) : "",
    starter ? el("div", { "data-new": "0.60.07-starter-dashboard" }, DA.spaces.startHere("Démarrez votre projet avec un assistant IA",
      "Répondez aux questions d'un assistant IA sur votre produit, votre industrie et votre marché : il prépare un fichier "
      + "qui crée votre Space, avec l'équipe, les requirements, les essais, les codes de temps et les premières pages.",
      [["Commencer", "#/admin/start", true]])) : "",
    el("div", { class: "db-top" + (messages ? "" : " db-top-single") }, messages, el("div", { class: "db-kpis" }, data.kpis.map(kpi))),
    el("div", { class: "db-grid" }, data.sections.map((s) => section(s, reload))),
    data.projects.length ? el("div", null, el("h2", { class: "db-projects-title" }, DA.t("dash.projects")),
      el("div", { class: "db-projects" }, data.projects.map((p) => el("span", { class: "key", title: p.name }, p.key)))) : "");
    if (!first) window.scrollTo(0, y);
  }

  DA.coreViews = DA.coreViews || {};
  /* D-A-044: left panel with the Dashboard logo */
  DA.coreViews.dashboard = (main) => render(DA.moduleLayout(main, { mark: DA.mark("dashboard"), label: "Dashboard",
    nav: [["#/dashboard", "Dashboard", true], ["#/settings", "Paramètres", false], ["#/objectives", "Mes objectifs", false]] }));
})();
