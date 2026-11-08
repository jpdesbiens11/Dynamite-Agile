/* « Testing » (D-B-079): the test team's portal, right after Goldmine in the top bar.
   #/testing                 -> the test base: filters (text, subject, standard, category, status, level, method,
                                requirements), counter, grouped by subject with the procedure page of each subject
   #/testing/subject/<code>  -> same, filtered on one subject (links of the procedure pages)
   #/testing/test/<ID>       -> a test record (testing_record.js)
   #/testing/lists           -> central lists: equipment, locations, product functions (testing_lists.js, D-B-082)
   « Exporter en Word » : the filtered tests as a test specification (D-B-083).
   D-B-097: one Test Base per Space -- #/testing/<KEY>/... (TESTING = the reference catalogue); the old addresses
   without a key open the catalogue. #/testing alone opens the default Space or the list of Spaces (D-B-098).
   Each Goldmine requirement names tests of its own Space's base in « Test Procedure ». */
(function () {
  "use strict";

  const { api, el, clear, field, toast, modal } = DA;
  const T = (DA.testing = DA.testing || {});
  const FILTER = {};  // filter values kept while the page is open
  const CAT_CLASS = { standard: "tg-cat-standard", industry: "tg-cat-industry", custom: "tg-cat-custom" };
  const STATUS_CLASS = { "Draft": "neutral", "In Review": "warn", "Approved": "ok", "Obsolete": "danger" };

  T.catBadge = (code, labels) => el("span", { class: "badge tg-cat " + (CAT_CLASS[code] || "") }, labels.categories[code] || code);
  T.statusBadge = (status) => el("span", { class: "badge badge-" + (STATUS_CLASS[status] || "neutral") }, status);
  /* 0.60.41 (D-O-050): the reference catalogue lives in DEMO; TESTING only on an installation made before */
  T.ref = () => ((DA.session.projects || []).some((p) => p.key === "TESTING") ? "TESTING" : "DEMO");
  T.pageHref = (page) => (page ? "#/dynamite/" + T.ref() + "/page/" + page.id : null);
  T.space = "";  // D-B-097: the Space whose Test Base is shown (set by the route)
  T.api = (url) => url + (url.indexOf("?") < 0 ? "?" : "&") + "space=" + encodeURIComponent(T.space);
  T.href = (rest) => "#/testing/" + T.space + (rest ? "/" + rest : "");
  T.reqHref = (key) => "#/goldmine/" + key.split("-")[0] + "/issue/" + key.split("-").slice(1).join("-");

  function mark() {
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 48 48");
    svg.setAttribute("class", "tg-mark");
    svg.setAttribute("aria-hidden", "true");
    [["path", { d: "M18 6h12M21 6v13L9 39a4 4 0 0 0 3.5 6h23A4 4 0 0 0 39 39L27 19V6" }],
      ["path", { d: "M14 31h20" }], ["circle", { cx: "21", cy: "37", r: "2" }], ["circle", { cx: "28", cy: "34", r: "1.5" }]]
      .forEach(([tag, attrs]) => {
        const n = document.createElementNS(NS, tag);
        Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
        n.setAttribute("fill", "none"); n.setAttribute("stroke", "currentColor"); n.setAttribute("stroke-width", "2.6");
        n.setAttribute("stroke-linecap", "round"); n.setAttribute("stroke-linejoin", "round");
        svg.append(n);
      });
    return svg;
  }
  T.mark = mark;

  T.head = function (title, text, actions) {
    return el("div", { class: "tg-head" }, el("div", { class: "tg-head-main" }, el("h1", null, title),
      text ? el("p", { class: "muted" }, text) : null), actions ? el("div", { class: "tg-actions" }, actions) : null);
  };

  function download(url) {
    const frame = el("iframe", { src: url, class: "ag-hidden-frame" });
    document.body.append(frame);
    setTimeout(() => frame.remove(), 15000);
  }

  /* ---------- New test ---------- */
  function openCreate(data, subject) {
    const L = data.labels;
    const sel = (map, value) => el("select", null, Object.entries(map).map(([k, v]) => el("option", { value: k, selected: k === value }, v)));
    const f = {
      title: el("input", { type: "text", maxlength: 200, required: true, placeholder: "ex. Test de chute sur chariot" }),
      subject: sel(L.subjects, subject || "func"), category: sel(L.categories, "custom"),
      test_id: el("input", { type: "text", maxlength: 30, placeholder: "vide = numéro suivant (ex. TST-CUS-23)" }),
      standard: el("input", { type: "text", maxlength: 200, value: "Test custom de l'équipe" }),
      section: el("input", { type: "text", maxlength: 200 }),
      level: el("select", null, L.levels.map((v) => el("option", { value: v, selected: v === "Module" }, v))),
      method: el("input", { type: "text", maxlength: 4, value: "T", placeholder: "T, A, I, D ou combinaison" }),
      objective: el("textarea", { rows: 3, maxlength: 3000, placeholder: "Ce que le test montre, et comment" }),
      acceptance: el("textarea", { rows: 2, maxlength: 2000, placeholder: "Mesurable ; [TBD] tant que le requirement ne le fixe pas" }),
    };
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      error.textContent = "";
      const body = Object.fromEntries(Object.entries(f).map(([k, input]) => [k, input.value]));
      try {
        const made = await api.post(T.api("/api/testing/tests"), body);
        close();
        toast(made.test_id + " créé (Brouillon).", "success");
        location.hash = T.href("test/" + made.test_id);
      } catch (err) { error.textContent = err.message; }
    } }, field("Title", f.title),
    el("div", { class: "form-row" }, field("Subject", f.subject), field("Category", f.category), field("Identifiant", f.test_id)),
    el("div", { class: "form-row" }, field("Standard / référence", f.standard), field("Section", f.section)),
    el("div", { class: "form-row" }, field("Level", f.level), field("Method (IADT)", f.method)),
    field("Objectif et déroulement", f.objective), field("Acceptance Criteria", f.acceptance), error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer le test")));
    close = modal("Nouveau Test", form);
    f.title.focus();
  }

  /* ---------- CSV import: preview, then apply ---------- */
  function importButton(reload) {
    const input = el("input", { type: "file", accept: ".csv,text/csv", class: "visually-hidden" });
    input.addEventListener("change", async () => {
      const file = input.files[0];
      input.value = "";
      if (!file) return;
      const text = await file.text();
      let preview;
      try { preview = await api.post(T.api("/api/testing/import"), { csv: text, mode: "preview" }); }
      catch (err) { toast(err.message, "error"); return; }
      const counts = {};
      preview.report.forEach((r) => { counts[r.status] = (counts[r.status] || 0) + 1; });
      let close = null;
      const rows = preview.report.filter((r) => r.status !== "inchangé").map((r) => el("tr", null,
        el("td", null, "Ligne " + r.line), el("td", { class: "nowrap" }, r.test_id), el("td", null, r.status),
        el("td", null, r.reason || r.changed.join(", "))));
      const content = el("div", null,
        el("p", null, Object.entries(counts).map(([s, n]) => n + " " + s).join(" · ") || "Aucune ligne."),
        rows.length ? DA.table(["Ligne", "Test", "Résultat", "Détail"], rows) : el("p", { class: "muted" }, "Rien ne change."),
        el("p", { class: "muted" }, "Aperçu : rien n'est encore écrit. Les lignes refusées sont ignorées."),
        el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
          el("button", { type: "button", class: "btn btn-primary", disabled: !(counts["créé"] || counts["mis à jour"]), onclick: async () => {
            try {
              const done = await api.post(T.api("/api/testing/import"), { csv: text, mode: "apply" });
              close();
              toast(done.report.filter((r) => r.status === "créé" || r.status === "mis à jour").length + " test(s) écrit(s).", "success");
              reload();
            } catch (err) { toast(err.message, "error"); }
          } }, "Appliquer")));
      close = modal("Import CSV — aperçu", content);
    });
    return el("label", { class: "btn btn-small tg-import" }, "Importer (CSV)", input);
  }

  /* ---------- The test base ---------- */
  async function listView(main, subject) {
    const data = await api.get(T.api("/api/testing/tests"));
    const L = data.labels;
    const reload = () => { clear(main); listView(main, subject); };
    const tests = data.tests;
    const hub = data.hub_page ? { id: data.hub_page } : null;
    let shown = tests;
    const exportBtn = el("button", { type: "button", class: "btn btn-small", onclick: () => {
      download(T.api("/api/testing/export.csv" + (shown.length === tests.length ? "" : "?ids=" + encodeURIComponent(shown.map((t) => t.test_id).join(",")))));
    } });
    const planBtn = el("button", { type: "button", class: "btn btn-small", onclick: () => T.newPlan(shown.map((t) => t.test_id)) },
      "Créer un plan de test");  // D-A-048
    const wordBtn = el("button", { type: "button", class: "btn btn-small", onclick: () => {
      if (!shown.length) return;
      DA.gt.wordDialog("Exporter en Word — spécification de tests", { title: "Test Specification",
        doctype: "Test Specification", note: shown.length + " test(s) : ceux affichés avec les filtres actuels." },
      [["subject", "Subject"], ["function", "Function"], ["location", "Test Location"]], (params) => {
        if (shown.length !== tests.length) params.set("ids", shown.map((t) => t.test_id).join(","));
        DA.gt.download(T.api("/api/testing/export.docx?" + params.toString()));
      });
    } }, "Exporter en Word (.docx)");
    main.append(T.head(data.reference ? "Testing — catalogue de référence" : "Testing — Test Base " + data.space,
      (data.reference ? "Modèle copié dans chaque Space à sa première ouverture ; les modifications ici ne touchent pas les "
        + "Spaces déjà copiés. " : "Base propre au Space " + data.space + " (copie du catalogue, modifiable sans toucher les "
        + "autres Spaces). ") + "Base des tests possibles d'un produit grand public mécatronique : standards (sécurité électrique, "
      + "CEM, IP, chute, durée de vie…), pratiques de l'industrie et custom tests de l'équipe. Chaque requirement Goldmine choisit ses tests "
      + "dans « Test Procedure » ; chaque sujet a sa procédure (wiki de référence, DEMO).", [
      hub ? el("a", { class: "btn btn-small", href: T.pageHref(hub) }, "Procedures (wiki)") : null,
      data.can_edit ? el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => openCreate(data, subject) }, "Nouveau Test") : null,
      exportBtn, wordBtn, planBtn, data.can_edit ? importButton(reload) : null,
      el("a", { class: "btn btn-small", href: T.href("lists") }, "Listes (équipements, lieux, fonctions)")]));

    const opt = (pairs, empty) => [el("option", { value: "" }, empty)].concat(pairs.map(([v, l]) => el("option", { value: v }, l)));
    const q = el("input", { type: "search", placeholder: "Filtrer (ID, titre, standard, objectif…)", "aria-label": "Filtrer" });
    const subj = el("select", { "aria-label": "Subject" }, opt(Object.entries(L.subjects), "All Subjects"));
    const standards = Array.from(new Set(tests.map((t) => t.standard))).sort();
    const std = el("select", { "aria-label": "Standard" }, opt(standards.map((s) => [s, s]), "All Standards"));
    const cat = el("select", { "aria-label": "Category" }, opt(Object.entries(L.categories), "All Categories"));
    const status = el("select", { "aria-label": "Status" }, opt(L.statuses.map((s) => [s, s]), "All Statuses"));
    const level = el("select", { "aria-label": "Level" }, opt(L.levels.map((s) => [s, s]), "All Levels"));
    const method = el("select", { "aria-label": "Method" }, opt(Object.entries(L.methods).map(([k, v]) => [k, k + " · " + v]), "All Methods"));
    const LI = data.lists;
    const loc = el("select", { "aria-label": "Test Location" }, opt(LI.location.map((x) => [x.code, x.label]).concat([["-", "Lieu à planifier"]]), "All Test Locations"));
    const equip = el("select", { "aria-label": "Test Equipment" }, opt(LI.equipment.map((x) => [x.code, x.code + " · " + x.label]), "All Test Equipment"));
    const func = el("select", { "aria-label": "Function" }, opt(LI.function.map((x) => [x.code, x.code + " · " + x.label])
      .concat([["-", "No Function"]]), "All Functions"));
    const has = (value, code) => (value || "").split(", ").includes(code);
    const linked = el("select", { "aria-label": "Requirements liées" }, opt([["yes", "Citées par un requirement"], ["no", "Sans requirement"]], "Liées ou non"));
    const controls = { q, subj, std, cat, status, level, method, loc, equip, func, linked };
    Object.entries(controls).forEach(([k, input]) => { if (FILTER[k]) input.value = FILTER[k]; });
    if (subject) subj.value = subject;
    const counter = el("div", { class: "gm-count", role: "status", "aria-live": "polite" });
    const result = el("div");
    const clearBtn = el("button", { type: "button", class: "link-btn", onclick: () => {
      Object.values(controls).forEach((i) => { i.value = ""; });
      if (subject) { location.hash = T.href(""); return; }
      draw();
    } }, "Effacer les filtres");
    main.append(el("div", { class: "ag-filters" }, Object.values(controls)), counter, result);

    function draw() {
      Object.entries(controls).forEach(([k, i]) => { FILTER[k] = k === "subj" ? "" : i.value; });
      const text = q.value.trim().toLowerCase();
      const list = tests.filter((t) => (!subj.value || t.subject === subj.value) && (!std.value || t.standard === std.value)
        && (!cat.value || t.category === cat.value) && (!status.value || t.status === status.value)
        && (!level.value || t.level === level.value) && (!method.value || (t.method || "").includes(method.value))
        && (!loc.value || (loc.value === "-" ? !t.location : t.location === loc.value))
        && (!equip.value || has(t.equipment, equip.value))
        && (!func.value || (func.value === "-" ? !t.functions : has(t.functions, func.value)))
        && (!linked.value || (linked.value === "yes" ? t.requirements > 0 : t.requirements === 0))
        && (!text || [t.test_id, t.title, t.standard, t.section, t.objective, t.acceptance, t.functions, t.equipment].join(" ").toLowerCase().includes(text)));
      shown = list;
      const filtered = list.length !== tests.length;
      clear(counter);
      counter.classList.toggle("gm-count-filtered", filtered);
      counter.append(el("strong", null, filtered ? list.length + " retenu(s) sur " + tests.length : list.length + " tests"),
        " · " + Object.entries(L.categories).map(([k, v]) => list.filter((t) => t.category === k).length + " " + v).join(" · ")
          + " · " + list.filter((t) => t.requirements > 0).length + " cité(s) par un requirement",
        filtered ? clearBtn : "");
      exportBtn.textContent = filtered ? "Exporter la sélection (" + list.length + ") (CSV)" : "Exporter (CSV)";
      exportBtn.disabled = !list.length;
      wordBtn.disabled = !list.length;
      wordBtn.textContent = filtered ? "Exporter la sélection en Word (" + list.length + ")" : "Exporter en Word (.docx)";
      planBtn.disabled = !list.length || list.length > 80;
      planBtn.textContent = "Créer un plan de test avec la sélection (" + list.length + ")";
      clear(result);
      Object.entries(L.subjects).forEach(([code, label]) => {
        const group = list.filter((t) => t.subject === code);
        if (!group.length) return;
        const proc = group[0].procedure;
        result.append(el("section", { class: "tg-group" },
          el("div", { class: "tg-group-head" }, el("h2", null, label, el("span", { class: "muted tg-n" }, " · " + group.length)),
            proc ? el("a", { class: "link-btn", href: T.pageHref(proc) }, "Procedure " + proc.title.split(" — ")[0] + " →") : null),
          DA.table(["Test", "Title", "Standard · section (source)", "Level", "Method", "Test Location", "Functions", "Category", "Status", "Requirements"],
            group.map((t) => el("tr", { class: t.status === "Obsolete" ? "tg-obsolete" : null },
              el("td", { class: "nowrap" }, el("a", { class: "ag-key", href: T.href("test/" + t.test_id) }, t.test_id)),
              el("td", null, el("strong", null, t.title)),
              el("td", null, t.standard, t.section ? el("div", { class: "muted" }, t.section) : null),
              el("td", { class: "nowrap" }, t.level), el("td", null, t.method),
              el("td", { class: "nowrap" }, t.location ? (LI.location.find((x) => x.code === t.location) || { label: t.location }).label
                : el("span", { class: "muted" }, "à planifier")),
              el("td", { class: "tg-funcs" }, t.functions || el("span", { class: "muted" }, "—")),
              el("td", null, T.catBadge(t.category, L)), el("td", null, T.statusBadge(t.status)),
              el("td", { class: "tg-num" }, t.requirements ? el("strong", null, String(t.requirements)) : el("span", { class: "muted" }, "0")))))));
      });
      if (!list.length) result.append(el("p", { class: "muted" }, "Aucun test ne correspond aux filtres."));
    }
    q.addEventListener("input", draw);
    [subj, std, cat, status, level, method, loc, equip, func, linked].forEach((s) => s.addEventListener("change", draw));
    draw();
  }

  /* D-B-098: #/testing alone -> the default Space, else the list of Spaces (the catalogue first) */
  function landing(main) {
    main.append(T.head("Testing", "Une Test Base par Space (D-B-097) : choisissez un Space. " + T.ref() + " porte le catalogue de "
      + "référence, copié dans un Space à sa première ouverture."));
    const ref = T.ref();
    const spaces = DA.session.projects.slice().sort((a, b) => (a.key === ref) - (b.key === ref));  // 0.60.41: own Spaces first
    main.append(el("div", { class: "project-list" }, spaces.map((p) =>
      el("a", { class: "project ag-project-card", href: "#/testing/" + p.key },
        el("div", { class: "project-top" }, el("span", { class: "key" }, p.key), p.key === ref ? DA.badge("Catalogue", "info") : DA.roleBadge(p.role)),
        el("h2", null, p.name), el("p", { class: "muted" }, p.description || "")))));
  }

  DA.registerModule("testing", async (shell, rawParts) => {
    let parts = rawParts.filter(Boolean);
    const keyed = parts[0] && /^[A-Z][A-Z0-9]{1,9}$/.test(parts[0]);
    const listing = !parts.length || parts[0] === "spaces";
    if (!parts.length && DA.spaces.enter("testing", parts, (k) => "#/testing/" + k)) return;
    T.space = keyed ? parts[0] : T.ref();  // the old addresses (#/testing/test/…) open the catalogue
    if (keyed) parts = parts.slice(1);
    /* D-A-044: left panel like the other modules, with the Testing logo */
    const view = parts[0] === "lists" ? "lists" : parts[0] === "plans" ? "plans" : parts[0] === "verification" ? "verification" : parts[0] === "test" ? "test" : "base";
    const main = DA.moduleLayout(shell, { mark: DA.mark("testing"), label: "Testing",
      /* D-B-103: the Space drop-down, as in Goldmine and Dynamite; a change keeps the same view (base, plans, lists) */
      picker: listing ? null : DA.spaces.picker(T.space, (k) => "#/testing/" + k + (view === "plans" || view === "lists" || view === "verification" ? "/" + view : "")),
      /* D-B-087: order of use -- choose tests, read their procedure, send a plan; the central lists (set-up) last */
      nav: listing ? [] : [[T.href(""), "Test Base · " + T.space, view === "base"], ["#/dynamite/" + T.ref(), "Test Procedures (wiki)", false],
        [T.href("plans"), "Test Plans (fournisseurs)", view === "plans"], [T.href("verification"), "Vérification des requirements", view === "verification"], [T.href("lists"), "Listes centrales", view === "lists"]],
      footer: listing ? DA.spaces.sidebar("testing", (k) => "#/testing/" + k, "") : DA.spaces.allLink("testing") });
    main.classList.add("tg-main");
    try {
      if (listing) landing(main);
      else if (parts[0] === "test" && parts[1]) await T.recordView(main, decodeURIComponent(parts[1]));
      else if (parts[0] === "plans" && parts[1]) await T.planView(main, decodeURIComponent(parts[1]));  // D-A-048
      else if (parts[0] === "plans") await T.plansView(main);
      else if (parts[0] === "lists") await T.listsView(main);
      else if (parts[0] === "verification") await T.verifyView(main);  // 0.60.91 (D-O-097)
      else await listView(main, parts[0] === "subject" ? parts[1] : "");
    } catch (err) {
      clear(main);
      main.append(el("div", { class: "empty" }, el("p", null, err.message)));
    }
  });
})();
