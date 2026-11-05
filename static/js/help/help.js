/* Help - top tab right of the tabs, after a vertical bar (D-B-024): the chronological guide
   (content_path.js), the FAQ (content_faq.js) and the HeadLamp learning
   project -- each chapter points to its HeadLamp step and to the tool.
   Chapters marked « fait » are remembered in this browser, per user. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const HELP = DA.help;
  HELP.path.forEach((c, i) => { c.step = i + 1; });  // 0.47.0: the number is the position in the tour
  const HL = "HEADLAMP";
  const TRY = {  // where to practise each chapter in HeadLamp
    bienvenue: ["#/dynamite/" + HL, "Ouvrir la page d'accueil HeadLamp [Sandbox]"],
    dashboard: ["#/dashboard", "Ouvrir le Dashboard"],
    testing: ["#/testing", "Ouvrir la Test Base"],
    training: ["#/training", "Ouvrir mon plan de formation"],
    projets: ["#/home", "Ouvrir l'Accueil"],
    dynamite: ["#/dynamite/" + HL, "Ouvrir Dynamite · HeadLamp [Sandbox]"],
    goldmine: ["#/goldmine/" + HL, "Ouvrir Goldmine · HeadLamp [Sandbox]"],
    exploration: ["#/exploration/" + HL + "/plan", "Ouvrir le plan HeadLamp [Sandbox]"],
    agile: ["#/agile/" + HL + "/board", "Ouvrir le tableau HeadLamp [Sandbox]"],
    changements: ["#/agile/" + HL + "/changes", "Ouvrir Change Management · HeadLamp [Sandbox]"],
    generator: ["#/codex/" + HL + "/generer", "Ouvrir Generator · HeadLamp [Sandbox]"],  // Tools → Generator
    timesheet: ["#/timesheet", "Ouvrir ma semaine"],
    "recherche-audit": ["#/audit", "Ouvrir la liste Audit"],
    administration: ["#/admin/users", "Ouvrir Admin"],
  };
  let headlamp = null;

  /* ---------- Per-user « done » marks (browser only) ---------- */
  const doneKey = () => "da.help.done." + (DA.session.user.id || "");
  function done() { try { return JSON.parse(localStorage.getItem(doneKey()) || "{}") || {}; } catch (err) { return {}; } }
  function setDone(id, value) {
    const d = done();
    if (value) d[id] = 1; else delete d[id];
    try { localStorage.setItem(doneKey(), JSON.stringify(d)); } catch (err) { /* private window */ }
  }

  /* ---------- Rendering of content blocks (text only) ---------- */
  function inline(text) {
    return String(text).split(/\*\*(.+?)\*\*/).map((part, i) => (i % 2 ? el("strong", null, part) : part));
  }
  function block(b) {
    const [kind, a, c] = b;
    switch (kind) {
      case "p": return el("p", null, inline(a));
      case "h": return el("h3", null, a);
      case "steps": return el("ol", { class: "hp-steps" }, a.map((x) => el("li", null, inline(x))));
      case "list": return el("ul", null, a.map((x) => el("li", null, inline(x))));
      case "tip": return el("div", { class: "hp-note hp-tip", role: "note" }, el("strong", null, "Astuce · "), inline(a));
      case "warn": return el("div", { class: "hp-note hp-warn", role: "note" }, el("strong", null, "Attention · "), inline(a));
      case "table": return DA.table(a, c.map((row) => el("tr", null, row.map((cell) => el("td", null, inline(cell))))));
      default: return null;
    }
  }
  const textOf = (blocks) => blocks.map((b) => [b[1], b[2]].flat(3).join(" ")).join(" ");

  /* ---------- Shell ---------- */
  function layout(main, active) {
    const page = el("section", { class: "ag-page hp-page" });
    const marks = done();
    const filter = el("input", { type: "search", class: "hp-filter", placeholder: "Chercher dans l'aide…", "aria-label": "Chercher dans l'aide" });
    filter.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && filter.value.trim()) location.hash = "#/help/chercher/" + encodeURIComponent(filter.value.trim()); });
    const count = HELP.path.filter((c) => marks[c.id]).length;
    main.append(el("div", { class: "ag-layout" },
      el("aside", { class: "ag-sidebar hp-sidebar" },
        el("a", { class: "hp-brand", href: "#/help" }, el("span", { class: "hp-brand-icon", "aria-hidden": "true" }, "?"), "Help"),
        filter,
        el("div", { class: "hp-progress", title: count + " chapitre(s) sur " + HELP.path.length + " marqué(s) « fait »" },
          el("div", { class: "hp-progress-bar" }, el("span", { class: "hp-progress-fill hp-w" + Math.round(10 * count / HELP.path.length) })),
          el("span", { class: "muted" }, count + " / " + HELP.path.length)),
        headlampCard(),
        el("nav", { class: "ag-nav hp-nav", "aria-label": "Chapitres de l'aide" },
          el("a", { class: "ag-nav-item" + (active === "home" ? " active" : ""), href: "#/help" }, "Vue d'ensemble"),
          HELP.path.map((c) => el("a", { class: "ag-nav-item" + (active === c.id ? " active" : ""), href: "#/help/" + c.id,
            "aria-current": active === c.id ? "page" : null, "data-new": c.isNew ? "0.47.0-help-" + c.id : null },
          el("span", { class: "hp-num" + (marks[c.id] ? " hp-num-done" : "") }, marks[c.id] ? "✓" : String(c.step)), c.title)),
          el("a", { class: "ag-nav-item" + (active === "faq" ? " active" : ""), href: "#/help/faq" }, el("span", { class: "hp-num" }, "?"), "FAQ"))),
      page));
    return page;
  }

  function headlampCard() {
    const box = el("div", { class: "hp-headlamp" }, el("strong", null, "HeadLamp [Sandbox]"),
      el("p", { class: "muted" }, "Le Space d'apprentissage : essayez chaque étape sans risque."));
    if (!headlamp || !headlamp.project) { box.append(el("p", { class: "muted" }, "Pas encore créé (redémarrez le serveur).")); return box; }
    if (headlamp.member) {
      box.append(el("a", { class: "btn btn-small", href: "#/dynamite/" + HL }, "Ouvrir le wiki HeadLamp [Sandbox]"));
    } else {
      box.append(el("button", { type: "button", class: "btn btn-primary btn-small", onclick: async () => {
        try { headlamp = await api.post("/api/help/headlamp/join"); toast("Bienvenue dans HeadLamp [Sandbox] !", "success"); location.hash = "#/dynamite/" + HL; }
        catch (err) { toast(err.message, "error"); }
      } }, "Rejoindre HeadLamp [Sandbox]"));
    }
    return box;
  }

  async function render(main, parts) {
    clear(main);
    main.classList.add("ag-main");
    try { headlamp = await api.get("/api/help/headlamp"); } catch (err) { headlamp = null; }
    const id = parts[0] || "home";
    if (id === "faq") return faqView(layout(main, "faq"));
    if (id === "chercher") return searchView(layout(main, ""), decodeURIComponent(parts[1] || ""));
    const chapter = HELP.path.find((c) => c.id === id);
    if (!chapter) return homeView(layout(main, "home"));
    chapterView(layout(main, chapter.id), chapter, main, parts);
  }

  /* ---------- Views ---------- */
  function homeView(page) {
    page.append(el("div", { class: "page-head" }, el("h1", null, "Help — guide de la plateforme"),
      el("p", { class: "muted" }, "Suivez les chapitres dans l'ordre : c'est l'ordre dans lequel un projet se met en place. "
        + "Chaque chapitre a son exercice dans le Space d'apprentissage HeadLamp [Sandbox].")),
    el("div", { class: "hp-cards" }, HELP.path.map((c) => el("a", { class: "hp-card" + (done()[c.id] ? " hp-card-done" : ""), href: "#/help/" + c.id,
      "data-new": c.isNew ? "0.47.0-help-" + c.id : null },  // D-A-049: chapters added by the tour of the site
      el("span", { class: "hp-card-step" }, "Étape " + c.step + " · " + c.tool), el("strong", null, c.title),
      el("span", { class: "muted" }, c.summary)))),
    docsSection(),
    el("h2", null, "Questions fréquentes"),
    el("ul", { class: "hp-faq-teaser" }, HELP.faq.slice(0, 4).map((f, i) => el("li", null, el("a", { href: "#/help/faq" }, f.q)))),
    el("a", { href: "#/help/faq" }, "Toute la FAQ →"));
  }

  /* 0.60.45 (D-O-054): the documentation of every module, pages of the HeadLamp library */
  function docsSection() {
    const docs = headlamp && headlamp.docs;
    if (!docs) return null;
    const href = (id) => "#/dynamite/" + HL + "/page/" + id;
    return el("section", { class: "hp-docs", "data-new": "0.60.45-module-docs" },
      el("h2", null, "Documentation des modules"),
      el("p", { class: "muted" }, "Pour chaque module : pourquoi il existe, le besoin couvert, le pas à pas, ce qu'on y fait de MVP 0 à "
        + "MVP x, et ses références de la plus à la moins pertinente. "
        + (headlamp.member ? "" : "Rejoignez HeadLamp [Sandbox] (panneau de gauche) pour lire ces pages.")),
      el("div", { class: "hp-cards" }, docs.modules.filter((m) => m.page).map((m) => el("a", { class: "hp-card", href: href(m.page) },
        el("span", { class: "hp-card-step" }, "Module"), el("strong", null, m.name), el("span", { class: "muted" }, m.role)))),
      el("a", { href: href(docs.hub) }, "Toute la documentation →"));
  }

  function chapterView(page, c, main, parts) {
    const i = HELP.path.indexOf(c);
    const prev = HELP.path[i - 1], next = HELP.path[i + 1];
    const step = headlamp && headlamp.by_chapter ? headlamp.by_chapter[c.id] : null;  // 0.47.0: by chapter, not by number
    const box = el("input", { type: "checkbox", checked: !!done()[c.id] });
    box.addEventListener("change", () => { setDone(c.id, box.checked); render(main, parts); });
    const [href, label] = TRY[c.id] || ["#/home", "Ouvrir"];
    page.append(
      el("div", { class: "page-head" }, el("span", { class: "hp-card-step" }, "Étape " + c.step + " sur " + HELP.path.length + " · " + c.tool),
        el("h1", null, c.title), el("p", { class: "muted" }, c.summary)),
      el("div", { class: "hp-body" }, c.blocks.map(block)),
      el("section", { class: "hp-try" }, el("h2", null, "Exercice HeadLamp [Sandbox]"),
        step ? el("p", null, "Ticket ", el("a", { href: "#/agile/" + HL + "/issue/" + step.number }, step.key),
          " — status : " + step.status + ". Lisez la consigne dans le ticket, puis faites l'exercice.")
          : el("p", { class: "muted" }, "Rejoignez HeadLamp [Sandbox] (panneau de gauche) pour faire l'exercice de cette étape."),
        el("a", { class: "btn", href }, label)),
      el("label", { class: "check hp-done" }, box, "J'ai terminé cette étape"),
      el("div", { class: "hp-pager" },
        prev ? el("a", { class: "btn", href: "#/help/" + prev.id }, "← " + prev.title) : el("span"),
        next ? el("a", { class: "btn btn-primary", href: "#/help/" + next.id }, next.title + " →")
          : el("a", { class: "btn btn-primary", href: "#/help/faq" }, "FAQ →")));
  }

  function faqView(page) {
    page.append(el("div", { class: "page-head" }, el("h1", null, "FAQ — ce qui n'est pas évident"),
      el("p", { class: "muted" }, "Le va-et-vient des données, l'aide d'un agent IA, et les questions qu'on se pose tous.")),
    el("div", { class: "hp-faq" }, HELP.faq.map((f, i) => el("details", { class: "hp-faq-item", open: i < 2 },
      el("summary", { "data-new": f.newTag || null }, f.q), el("div", { class: "hp-body" }, f.blocks.map(block))))));
  }

  function searchView(page, query) {
    const words = query.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").split(/\s+/).filter(Boolean);
    const fold = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    const hit = (s) => words.every((w) => fold(s).includes(w));
    const chapters = HELP.path.filter((c) => hit(c.title + " " + c.summary + " " + textOf(c.blocks)));
    const faqs = HELP.faq.filter((f) => hit(f.q + " " + textOf(f.blocks)));
    page.append(el("div", { class: "page-head" }, el("h1", null, "Aide : « " + query + " »"),
      el("p", { class: "muted" }, (chapters.length + faqs.length) + " résultat(s)")),
    el("ul", { class: "hp-results" },
      chapters.map((c) => el("li", null, el("a", { href: "#/help/" + c.id }, "Étape " + c.step + " — " + c.title), el("span", { class: "muted" }, " · " + c.summary))),
      faqs.map((f) => el("li", null, el("a", { href: "#/help/faq" }, "FAQ — " + f.q)))));
  }

  DA.registerModule("help", render);
})();
