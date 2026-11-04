/* Dynamite - module shell: black left panel with the logo, space picker and
   page tree; page view, history (compare + restore), creation and editing.
   URL: #/dynamite/<KEY>[/page/<id>[/edit|/history]] or #/dynamite/<KEY>/new[/<parentId>] */
(function () {
  "use strict";

  const { api, el, clear, toast, modal } = DA;
  const DY = DA.dynamite;

  function base(ctx) { return "/api/dynamite/p/" + ctx.pid + "/pages"; }
  function pageHref(ctx, id, suffix) { return "#/dynamite/" + ctx.key + "/page/" + id + (suffix || ""); }
  function canEdit(ctx) { return ctx.role === "editor" || ctx.role === "admin"; }

  /* ---------- Left panel: tree ---------- */
  function tree(ctx, activeId) {
    const byParent = new Map();
    ctx.pages.forEach((p) => {
      const k = p.parent_id || 0;
      if (!byParent.has(k)) byParent.set(k, []);
      byParent.get(k).push(p);
    });
    const open = new Set();
    let walk = ctx.pages.find((p) => p.id === activeId);
    while (walk) { open.add(walk.id); walk = ctx.pages.find((p) => p.id === walk.parent_id); }
    function level(parentId) {
      const kids = byParent.get(parentId) || [];
      if (!kids.length) return null;
      return el("ul", { class: "dy-tree" }, kids.map((p) => {
        const hasKids = byParent.has(p.id);
        const item = el("li", { class: "dy-tree-item" + (open.has(p.id) ? " open" : "") },
          el("span", { class: "dy-tree-row" + (p.id === activeId ? " active" : "") },
            hasKids ? el("button", { type: "button", class: "dy-twisty", "aria-label": "Déplier " + p.title,
              onclick: () => item.classList.toggle("open") }, "▸") : el("span", { class: "dy-twisty-space" }),
            el("a", { href: pageHref(ctx, p.id), "aria-current": p.id === activeId ? "page" : null }, p.title)),
          level(p.id));
        return item;
      }));
    }
    return level(0) || el("p", { class: "dy-muted-sm" }, "Aucune page dans ce Space.");
  }

  function sidebar(ctx, activeId) {
    const picker = el("select", { class: "dy-space-picker", "aria-label": "Space",
      onchange: (ev) => { location.hash = "#/dynamite/" + ev.target.value; } },
    DA.session.projects.map((p) => el("option", { value: p.key, selected: p.key === ctx.key }, p.key + " · " + p.name)));
    return el("aside", { class: "dy-sidebar" },
      el("img", { src: DA.mark("dynamite"), alt: "", class: "dy-mark-img" }),
      picker,
      canEdit(ctx) ? el("a", { class: "btn btn-small dy-new", href: "#/dynamite/" + ctx.key + "/new" }, "+ Nouvelle page") : null,
      el("div", { class: "dy-tree-title" }, "Pages"),
      tree(ctx, activeId), DA.spaces.allLink("dynamite"));  // D-B-098
  }

  function crumbs(ctx, list, last) {
    return el("nav", { class: "dy-crumbs", "aria-label": "Fil d'Ariane" },
      el("a", { href: "#/dynamite/" + ctx.key }, ctx.project.name),
      list.flatMap((c) => [el("span", { class: "dy-sep" }, "/"), el("a", { href: pageHref(ctx, c.id) }, c.title)]),
      last ? [el("span", { class: "dy-sep" }, "/"), el("span", null, last)] : null);
  }

  /* ---------- Page view ---------- */
  async function viewPage(page, ctx, id) {
    const data = await api.get(base(ctx) + "/" + id);
    const p = data.page;
    const actions = el("div", { class: "dy-actions dy-actions-top", role: "toolbar", "aria-label": "Actions sur la page" },
      canEdit(ctx) ? el("a", { class: "btn btn-primary btn-small", href: pageHref(ctx, id, "/edit") }, "Modifier") : null,
      canEdit(ctx) ? el("a", { class: "btn btn-small", href: "#/dynamite/" + ctx.key + "/new/" + id }, "+ Sous-page") : null,
      el("a", { class: "btn btn-small", href: pageHref(ctx, id, "/history") }, "Historique"),
      DY.canTransfer() ? el("button", { type: "button", class: "btn btn-small", onclick: () => DY.transferDialog(ctx, p) }, "Déplacer / Copier") : null,
      DY.exportMenu(ctx, p),
      ctx.key === "HEADLAMP" ? el("a", { class: "btn btn-small dy-help-link", href: "#/help" }, "📘 Guide Help") : null,
      ctx.role === "admin" ? el("button", { type: "button", class: "btn btn-small btn-danger", onclick: async () => {
        if (!window.confirm("Supprimer « " + p.title + " » et tout son historique ?")) return;
        try { await api.del(base(ctx) + "/" + id); toast("Page supprimée.", "success"); location.hash = "#/dynamite/" + ctx.key; }
        catch (err) { toast(err.message, "error"); }
      } }, "Supprimer") : null);
    // Page menu between the breadcrumb and the title (D-B-012), clear of the content's own links.
    page.append(...[crumbs(ctx, data.crumbs), actions, el("h1", { class: "dy-page-title" }, p.title),
      el("p", { class: "dy-meta" }, "Version " + p.version + " · modifiée par " + p.updated_by + " · "
        + DA.formatDate(p.updated_at)),
      data.lock ? el("p", { class: "dy-lock" }, "✎ " + data.lock.by + " est en train de modifier cette page.") : null,
      DY.render(p.body, { children: data.children.map((c) => ({ title: c.title, href: pageHref(ctx, c.id) })) })]
      .filter(Boolean));
    // No second list when the page already shows its sub-pages with a « Sous-pages » block.
    if (data.children.length && !(p.body.content || []).some((b) => b.type === "children")) {
      page.append(el("section", { class: "dy-children" }, el("h2", null, "Sous-pages"),
        el("ul", null, data.children.map((c) => el("li", null, el("a", { href: pageHref(ctx, c.id) }, c.title))))));
    }
    page.append(DY.commentsSection(ctx, id));
  }

  /* ---------- History: compare with current, restore ---------- */
  function lineDiff(before, after) {
    const a = before.split("\n"), b = after.split("\n");
    if (a.length * b.length > 4e6) return [{ kind: "same", text: "(pages trop longues pour la comparaison ligne à ligne)" }];
    const dp = Array.from({ length: a.length + 1 }, () => new Uint32Array(b.length + 1));
    for (let i = a.length - 1; i >= 0; i--) for (let j = b.length - 1; j >= 0; j--)
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    const out = [];
    let i = 0, j = 0;
    while (i < a.length && j < b.length) {
      if (a[i] === b[j]) { out.push({ kind: "same", text: a[i] }); i++; j++; }
      else if (dp[i + 1][j] >= dp[i][j + 1]) out.push({ kind: "del", text: a[i++] });
      else out.push({ kind: "add", text: b[j++] });
    }
    while (i < a.length) out.push({ kind: "del", text: a[i++] });
    while (j < b.length) out.push({ kind: "add", text: b[j++] });
    return out;
  }

  async function history(page, ctx, id) {
    const [data, current] = await Promise.all([api.get(base(ctx) + "/" + id + "/versions"),
      api.get(base(ctx) + "/" + id)]);
    const detail = el("div", { class: "dy-version-detail" }, el("p", { class: "muted" }, "Choisissez une version à comparer."));
    async function show(v) {
      const [old, now] = await Promise.all([api.get(base(ctx) + "/" + id + "/versions/" + v.version),
        api.get(base(ctx) + "/" + id + "/versions/" + data.current)]);
      clear(detail);
      detail.append(el("div", { class: "dy-page-head" }, el("h2", null, "Version " + v.version + " → version actuelle " + data.current),
        canEdit(ctx) && v.version !== data.current ? el("button", { type: "button", class: "btn btn-small", onclick: async () => {
          try {
            await api.post(base(ctx) + "/" + id + "/versions/" + v.version + "/restore");
            toast("Version " + v.version + " restaurée comme nouvelle version (rien n'est effacé).", "success");
            location.hash = pageHref(ctx, id);
          } catch (err) { toast(err.message, "error"); }
        } }, "Restaurer cette version") : null),
      el("pre", { class: "dy-diff" }, lineDiff(DY.serialize(old.body), DY.serialize(now.body)).map((d) =>
        el("div", { class: "dy-diff-" + d.kind }, (d.kind === "add" ? "+ " : d.kind === "del" ? "− " : "  ") + d.text))));
    }
    page.append(crumbs(ctx, current.crumbs.concat([{ id, title: current.page.title }]), "Historique"),
      el("h1", null, "Historique"),
      el("div", { class: "dy-history" },
        el("ul", { class: "dy-versions" }, data.versions.map((v) => el("li", null,
          el("button", { type: "button", class: "dy-version-btn", onclick: () => show(v) },
            el("strong", null, "v" + v.version), " · " + (v.author || "—") + " · " + DA.formatDate(v.created_at),
            v.note ? el("div", { class: "muted" }, v.note) : null)))),
        detail));
  }

  /* ---------- Space home and routing ---------- */
  function spacePicker(main) {
    main.append(el("div", { class: "dy-layout" },
      el("aside", { class: "dy-sidebar" }, el("img", { src: DA.mark("dynamite"), alt: "", class: "dy-mark-img" }),
        DA.spaces.sidebar("dynamite", (k) => "#/dynamite/" + k)),  // D-B-098
      el("section", { class: "dy-page" }, el("h1", null, "Dynamite"),
        el("p", { class: "muted" }, "Choisissez un Space."),
        el("div", { class: "dy-spaces" }, DA.session.projects.map((p) => el("a", { class: "dy-space-card", href: "#/dynamite/" + p.key },
          el("span", { class: "dy-space-key" }, p.key), el("strong", null, p.name)))))));
  }

  async function render(main, parts) {
    clear(main);
    main.classList.add("dy-main");
    const key = (parts[0] || "").toUpperCase();
    const project = DA.session.projects.find((p) => p.key === key);
    if (!project) {
      if (DA.spaces.enter("dynamite", parts, (k) => "#/dynamite/" + k)) return;
      spacePicker(main);
      return;
    }
    const ctx = { key, pid: project.id };
    ctx.refresh = () => render(main, parts);
    let treeData;
    try { treeData = await api.get(base(ctx)); } catch (err) { main.append(el("p", { class: "form-error" }, err.message)); return; }
    Object.assign(ctx, { pages: treeData.pages, role: treeData.role, project: treeData.project });
    const view = parts[1];
    const id = Number(parts[2]) || null;
    const page = el("section", { class: "dy-page" });
    main.append(el("div", { class: "dy-layout" }, sidebar(ctx, id), page));
    try {
      if (view === "page" && parts[3] === "edit") {
        const data = await api.get(base(ctx) + "/" + id);
        await DY.openEditor(page, ctx, data.page);
      } else if (view === "page" && parts[3] === "history") {
        await history(page, ctx, id);
      } else if (view === "page" && id) {
        await viewPage(page, ctx, id);
      } else if (view === "new") {
        ctx.parentId = Number(parts[2]) || null;
        if (!canEdit(ctx)) throw new Error("Lecture seule : il faut le rôle éditeur sur ce Space pour créer une page.");
        await DY.openEditor(page, ctx, null);
      } else {
        const first = ctx.pages.find((p) => !p.parent_id);
        if (first) { location.replace(pageHref(ctx, first.id)); return; }  // D-B-096: no history trap
        page.append(el("h1", null, ctx.project.name), el("div", { class: "empty" },
          el("p", null, "Ce Space est vide."),
          canEdit(ctx) ? el("a", { class: "btn btn-primary", href: "#/dynamite/" + ctx.key + "/new" }, "Créer la première page")
            : el("p", { class: "muted" }, "Un éditeur du Space peut créer la première page.")));
      }
    } catch (err) {
      page.append(el("p", { class: "form-error" }, err.message));
    }
  }

  DA.registerModule("dynamite", render);
})();
