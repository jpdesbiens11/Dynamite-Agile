/* Generator (ex-Codex, key "codex") - top tab (D-B-021, renamed D-B-022): naming and filing of the documents of a
   project along the product development process (MIP, RCS, CdCF, RC, RVE...). « Générer » previews the reference live (browser clock) and
   reserves it: the server stamps the final, unique number. « Registre »
   lists what was reserved (registry.js). */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const CX = DA.codex;
  const EPOCH = Date.UTC(1899, 11, 30);  // Excel serial epoch
  const FORBIDDEN = /[\\/:*?"<>|\u0000-\u001f]/g;
  const NAV = [["generer", "Générer"], ["registre", "Registre"]];

  const mark = () => el("img", { src: DA.mark("generator"), alt: "", class: "cx-mark-img" });

  /* ---------- Naming rules (mirror of modules/codex/catalog.py) ---------- */
  function serialParts(date) {
    const days = (date.getTime() - EPOCH) / 86400000;
    let d = Math.floor(days);
    let t = Math.round((days - d) * 100000);
    if (t >= 100000) { d += 1; t = 0; }
    return [d, t];
  }
  const pad5 = (n) => String(n).padStart(5, "0");

  function build(meta, f, d, t) {
    const ref = f.type + "-" + pad5(d) + "-" + pad5(t);
    const title = f.title.replace(FORBIDDEN, "-").replace(/\s+/g, " ").replace(/^[\s.]+|[\s.]+$/g, "");
    let fileName = ref + "_" + f.revision;
    if (f.system) fileName += "_" + f.system;
    if (title) fileName += " " + title;
    const step = meta.steps[f.chapter];
    const sys = f.system && f.system !== step.label ? f.system : step.label;
    const svn = "Documents/" + meta.types[f.type].folder + "/" + f.chapter + "-" + f.sub + "_" + sys + "/";
    return { reference: ref, file_name: fileName, svn_path: svn };
  }

  /* ---------- Shell ---------- */
  function layout(main, ctx, active) {
    const page = el("section", { class: "ag-page cx-page" });
    main.append(el("div", { class: "ag-layout" },
      el("aside", { class: "ag-sidebar ag-shell-codex" },
        el("div", { class: "ag-sidebar-mark" }, mark()),
        ctx ? el("select", { class: "ag-project-picker", "aria-label": "Space",
          onchange: (ev) => { location.hash = "#/codex/" + ev.target.value + "/" + active; } },
        DA.session.projects.map((p) => el("option", { value: p.key, selected: p.key === ctx.key }, p.key + " · " + p.name))) : null,
        ctx ? el("nav", { class: "ag-nav", "aria-label": "Generator" }, NAV.map(([v, label]) =>
          el("a", { class: "ag-nav-item" + (active === v ? " active" : ""), href: "#/codex/" + ctx.key + "/" + v,
            "aria-current": active === v ? "page" : null }, label))) : null),
      page));
    return page;
  }

  function picker(main) {
    const page = layout(main, null);
    page.append(el("div", { class: "page-head" }, el("h1", null, "Generator"),
      el("p", { class: "muted" }, "Nommage et classement des documents du projet, étape par étape du PDP (MIP, RCS, CdCF, RC, RVE…). "
        + "Choisissez un Space.")));
    if (!DA.session.projects.length) { page.append(el("div", { class: "empty" }, el("p", null, "Aucun Space accessible."))); return; }
    page.append(el("div", { class: "project-list" }, DA.session.projects.map((p) =>
      el("a", { class: "project ag-project-card", href: "#/codex/" + p.key + "/generer" },
        el("div", { class: "project-top" }, el("span", { class: "key" }, p.key), DA.roleBadge(p.role)),
        el("h2", null, p.name), el("p", { class: "muted" }, p.description || "Aucune description.")))));
  }

  async function render(main, parts) {
    clear(main);
    main.classList.add("ag-main");
    if (DA.spaces.enter("codex", parts, (k) => "#/codex/" + k)) return;  // D-B-134: straight to the default Space
    const key = (parts[0] || "").toUpperCase();
    const project = DA.session.projects.find((p) => p.key === key);
    if (!project) { picker(main); return; }
    const view = parts[1] === "registre" ? "registre" : "generer";
    const ctx = { key, pid: project.id, project, initialQuery: view === "registre" ? decodeURIComponent(parts[2] || "") : "" };
    const page = layout(main, ctx, view);
    try {
      await CX.loadMeta();
      ctx.data = await api.get(CX.base(ctx) + "/refs");
      if (view === "registre") CX.registryView(page, ctx, () => render(main, parts));
      else generator(page, ctx);
    } catch (err) {
      page.append(el("div", { class: "empty" }, el("p", null, err.message)));
    }
  }

  /* ---------- Generator view ---------- */
  function groupedSelect(label, groups, items, value, selected) {
    return el("select", { "aria-label": label }, groups.map((g) => el("optgroup", { label: g.group },
      g[items].map((it) => el("option", { value: value(it), selected: value(it) === selected }, it.__label)))));
  }

  function generator(page, ctx) {
    const meta = CX.meta;
    meta.doc_groups.forEach((g) => g.types.forEach((t) => { t.__label = t.code + " — " + t.name; }));
    meta.step_groups.forEach((g) => g.steps.forEach((c) => {
      c.__label = c.step + " — " + c.name + (c.note ? " (" + c.note + ")" : "");
    }));
    const type = groupedSelect("Type de document", meta.doc_groups, "types", (t) => t.code, "CDCF");
    const chapter = groupedSelect("Étape du PDP", meta.step_groups, "steps", (c) => c.step, "11");
    const sub = el("input", { type: "text", maxlength: 2, placeholder: "00", inputmode: "numeric" });
    /* D-B-106: the title takes the name of the chosen type (until it is typed by hand), and the Project ID (the Space
       name in capitals when it is one word, else its key) ends the title; the system code is optional */
    const system = el("input", { type: "text", maxlength: 20, value: "", placeholder: "ex. CHAUF" });
    const revision = el("input", { type: "number", value: 1, min: 1, max: 99 });
    const title = el("input", { type: "text", maxlength: 120, placeholder: "Cahier des charges fonctionnel", "data-new": "0.50.1-cx-title" });
    const projectId = el("input", { type: "text", maxlength: 20, value: CX.projectId(ctx.project), placeholder: CX.projectId(ctx.project),
      "data-new": "0.50.1-cx-project" });
    let titleAuto = true;
    const typeName = () => (meta.types[type.value] || {}).name || "";
    title.value = typeName();
    title.addEventListener("input", () => { titleAuto = !title.value.trim(); });
    type.addEventListener("change", () => { if (titleAuto) title.value = typeName(); });

    const clockNum = el("span", { class: "cx-clock-num" });
    const clockHuman = el("span", { class: "cx-clock-human" });
    const outState = el("span", { class: "cx-out-state" });
    const outs = { reference: el("div", { class: "cx-out-value cx-out-ref" }),
      file_name: el("div", { class: "cx-out-value" }), svn_path: el("div", { class: "cx-out-value cx-out-svn" }) };
    let reserved = null;  // server copy of the last reservation, shown until the form changes

    function form() {
      const s = sub.value.trim();
      return { type: type.value, chapter: chapter.value, sub: /^\d{1,2}$/.test(s) ? s.padStart(2, "0") : "00",
        system: system.value.trim().toUpperCase(), revision: Math.min(99, Math.max(1, parseInt(revision.value, 10) || 1)),
        title: [title.value.trim(), projectId.value.trim()].filter(Boolean).join(" ") };
    }

    function update() {
      const now = new Date();
      const [d, t] = serialParts(now);
      clockNum.textContent = pad5(d) + "-" + pad5(t);
      clockHuman.textContent = now.toLocaleString("fr-CA", { dateStyle: "medium", timeStyle: "medium" }) + " (UTC "
        + now.toISOString().slice(11, 19) + ")";
      const shown = reserved || build(meta, form(), d, t);
      Object.keys(outs).forEach((k) => { outs[k].textContent = shown[k]; });
      outState.textContent = reserved ? "✓ Réservée dans " + ctx.key : "Aperçu — le numéro final est donné à la réservation";
      outState.classList.toggle("cx-out-reserved", !!reserved);
    }

    [type, chapter, sub, system, revision, title, projectId].forEach((c) => {
      c.addEventListener("input", () => { reserved = null; update(); });
      c.addEventListener("change", () => { reserved = null; update(); });
    });
    const timer = setInterval(() => { if (!page.isConnected) { clearInterval(timer); return; } if (!reserved) update(); }, 1000);

    async function reserve() {
      const f = form();
      try {
        const res = await api.post(CX.base(ctx) + "/refs", { doc_type: f.type, step: f.chapter, sub: sub.value,
          system_code: f.system, revision: revision.value, title: f.title });
        reserved = res.ref;
        ctx.data.refs.unshift(res.ref);
        update();
        drawRecent();
        toast("Référence " + res.ref.reference + " réservée.", "success");
      } catch (err) { toast(err.message, "error"); }
    }

    const outBox = (label, key) => el("div", { class: "cx-out" },
      el("div", { class: "cx-out-head" }, el("span", null, label), key === "file_name" ? null : CX.copyButton(() => outs[key].textContent)),
      key === "file_name"  // D-B-106: « Copier » right after the final name, ready for the name field of MS Word
        ? el("div", { class: "cx-out-line" }, outs[key], el("span", { "data-new": "0.50.1-cx-copy-name" },
          CX.copyButton(() => outs[key].textContent, "Copier le nom"))) : outs[key]);

    const recent = el("div", { class: "cx-recent" });
    function drawRecent() {
      clear(recent);
      const refs = ctx.data.refs.filter((r) => r.status === "active").slice(0, 5);
      if (!refs.length) return;
      recent.append(el("h2", null, "Dernières réservations"), el("ul", { class: "cx-recent-list" }, refs.map((r) =>
        el("li", null, el("span", { class: "cx-mono" }, r.file_name), " ",
          el("span", { class: "muted cx-small" }, "· " + (r.created_by_name || "") + " · " + DA.formatDate(r.created_at)),
          " ", CX.copyButton(r.file_name, "Copier")))),
      el("a", { href: "#/codex/" + ctx.key + "/registre" }, "Voir tout le registre →"));
    }

    page.append(
      el("div", { class: "page-head" }, el("h1", null, "Generator — " + ctx.project.name),
        el("p", { class: "muted" }, "Référence, nom de fichier et dossier d'un document, types rangés selon les quatre phases du "
          + "processus de développement de produit : pré-étude, étude conceptuelle, conception, fabrication et validation.")),
      el("div", { class: "cx-clock" },
        el("div", null, el("div", { class: "cx-clock-label" }, "Date-heure série Excel (maintenant, UTC)"), clockNum, clockHuman)),
      el("div", { class: "cx-grid" },
        DA.field("Type de document", type), DA.field("Étape du PDP", chapter),
        DA.field("Subdivision", sub, "Optionnelle, ex. 03 (vide = 00)."),
        DA.field("Code système", system, "Optionnel, ex. CHAUF (sous-système de chauffage). Remplace le libellé de l'étape dans le dossier."),
        DA.field("Révision", revision),
        DA.field("Titre du document", title, "Pris du type choisi ; modifiable. Effacez-le pour revenir au nom du type."),
        DA.field("Project ID", projectId, "Ajouté à la fin du titre. Nom du Space en majuscules, ou sa clé.")),
      el("div", { class: "cx-outs" }, el("div", { class: "cx-outs-bar" }, outState, el("span", { class: "cx-spacer" }),
        ctx.data.can_edit ? el("button", { type: "button", class: "btn btn-primary", onclick: reserve }, "Réserver la référence")
          : el("span", { class: "muted cx-small" }, "Lecture seule : un éditeur du Space réserve les numéros.")),
      outBox("Référence", "reference"), outBox("Nom de fichier complet", "file_name"), outBox("Dossier", "svn_path")),
      recent, references(meta),
      el("p", { class: "cx-note" }, el("strong", null, "Méthode de numérotation : "), "la date-heure série Excel (jours depuis "
        + "le 30 déc. 1899, en UTC) coupée en deux blocs de 5 chiffres — partie entière (date) et fraction × 100 000 "
        + "(heure). Le serveur garantit qu'un numéro n'est donné qu'une fois dans toute la plateforme. "
        + "Convention : TYPE-DDDDD-TTTTT_RÉV_SYSTÈME Titre Project ID."));
    update();
    drawRecent();
  }

  /* ---------- Quick reference tables ---------- */
  function references(meta) {
    const folders = {};
    Object.values(meta.types).forEach((t) => { (folders[t.folder] = folders[t.folder] || []).push(t.code); });
    const section = (label, headers, rows) => el("details", { class: "cx-ref-table" }, el("summary", null, label),
      DA.table(headers, rows.map((r) => el("tr", null, r.map((c, i) => el("td", { class: i ? null : "cx-mono" }, c))))));
    return el("div", { class: "cx-refs" },
      section("Types de documents — référence rapide", ["Code", "Nom", "Origine", "Dossier"],
        Object.values(meta.types).map((t) => [t.code, t.name, t.standard, t.folder])),
      section("Étapes du PDP — classement des documents", ["Étape", "Libellé", "Nom", "Livrable"],
        Object.values(meta.steps).map((c) => [c.step, c.label, c.name, c.note || "—"])),
      section("Arborescence des livrables", ["Dossier", "Contenu"],
        Object.keys(folders).sort().map((f) => [f, folders[f].join(", ")])));
  }

  DA.registerModule("codex", render);
})();
