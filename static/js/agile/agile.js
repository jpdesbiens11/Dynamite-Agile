/* Agile - module shell: project picker, side navigation, shared helpers.
   Screens live in issue.js, board.js and settings.js and register themselves
   in DA.agile.views. URL: #/agile/<KEY>/<view>[/<number>]. */
(function () {
  "use strict";

  const { api, el, clear, toast, initials } = DA;

  const TYPE_GLYPHS = { epic: "⚡", story: "▮", task: "✓", bug: "●", subtask: "↳", requirement: "§", ecn: "Δ", pr: "⚑" };
  const PRIORITY = {
    blocker: { label: "Bloquante", glyph: "⇈" },
    high: { label: "Haute", glyph: "↑" },
    medium: { label: "Moyenne", glyph: "=" },
    low: { label: "Basse", glyph: "↓" },
    trivial: { label: "Minime", glyph: "⇊" },
  };
  const CATEGORY_LABELS = { todo: "To Do", in_progress: "In Progress", done: "Done" };
  const LINK_LABELS = {
    blocks: { out: "bloque", in: "est bloqué par" },
    relates: { out: "est lié à", in: "est lié à" },
    duplicates: { out: "duplique", in: "est dupliqué par" },
    implements: { out: "implémente", in: "est implémenté par" },
    resolves: { out: "traite", in: "est traité par" },
  };
  const ROLE_LEVEL = { reader: 1, editor: 2, admin: 3 };

  /* ---------- Brand pictograms (redrawn from the user's reference images
     as flat line art: currentColor, no gradients, no text in the SVG) ---------- */
  function staticSvg(markup) {
    // Only ever called below with a hardcoded literal -- never with server
    // or user data, so this is not the innerHTML-on-server-data pattern
    // the security rule forbids; el()/textContent still handle all data.
    const template = document.createElement("template");
    template.innerHTML = markup.trim();
    return template.content.firstChild;
  }

  function moduleMark() {
    // Cave-arch-and-light mark, after the "Agile" reference image.
    return staticSvg(
      '<svg viewBox="0 0 24 24" class="ag-mark" aria-hidden="true">' +
      '<path d="M3 21 L3 13 Q3 5 12 5 Q21 5 21 13 L21 21" fill="none" ' +
      'stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>' +
      '<circle cx="12" cy="14.5" r="2.1" fill="currentColor"/>' +
      '</svg>');
  }

  function roadmapIcon() {
    // Folded map with a dashed route and a pin, after the reference image;
    // used for the Backlog screen (a backlog is, in effect, a roadmap).
    return staticSvg(
      '<svg viewBox="0 0 24 24" class="ag-mark ag-mark-sm" aria-hidden="true">' +
      '<path d="M3 5 L9 3 L15 5 L21 3 L21 19 L15 21 L9 19 L3 21 Z" fill="none" ' +
      'stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>' +
      '<path d="M9 3 L9 19 M15 5 L15 21" stroke="currentColor" stroke-width="1" ' +
      'stroke-dasharray="1.5 2" opacity="0.55"/>' +
      '<path d="M6 16 Q10 10.5 13.5 12 T18.5 7" fill="none" stroke="currentColor" ' +
      'stroke-width="1.5" stroke-linecap="round" stroke-dasharray="2.2 2.2"/>' +
      '<circle cx="18.7" cy="6.8" r="1.9" fill="currentColor"/>' +
      '</svg>');
  }

  /* ---------- Small shared builders ---------- */
  function typeIcon(iconKey, name) {
    return el("span", { class: "ag-type ag-type-" + iconKey, title: name, "aria-label": name },
      TYPE_GLYPHS[iconKey] || "•");
  }

  function priorityIcon(priority) {
    const p = PRIORITY[priority] || PRIORITY.medium;
    return el("span", { class: "ag-prio ag-prio-" + priority, title: "Priority " + p.label.toLowerCase(),
      "aria-label": "Priority " + p.label.toLowerCase() }, p.glyph);
  }

  function statusBadge(name, category) {
    return el("span", { class: "ag-status ag-status-" + category }, name);
  }

  const labelColors = new Map();
  function labelChip(name) {
    const color = labelColors.get(String(name).toLowerCase()) || "neutral";
    return el("span", { class: "ag-label ag-label-" + color }, name);
  }

  function avatar(name) {
    if (!name) return el("span", { class: "ag-avatar ag-avatar-empty", title: "Non assigné" }, "–");
    return el("span", { class: "ag-avatar", title: name }, initials(name));
  }

  /* Route inside the current shell: Agile or Goldmine (D-B-011). */
  function href(ctx, rest) { return "#/" + (ctx.module || "agile") + "/" + ctx.key + "/" + rest; }

  function issueLink(ctx, issue, text) {
    return el("a", { class: "ag-key", href: href(ctx, "issue/" + issue.number) }, text || issue.key);
  }

  /* Plain text with clickable http(s) links; never parsed as HTML. */
  function richText(text) {
    const box = el("div", { class: "ag-text" });
    const parts = String(text || "").split(/(https?:\/\/[^\s<>"]+)/g);
    parts.forEach((part, i) => {
      if (i % 2 === 1) box.append(el("a", { href: part, rel: "noopener noreferrer" }, part));
      else if (part) box.append(part);
    });
    return box;
  }

  function options(items, selected, emptyLabel) {
    const list = [];
    if (emptyLabel !== undefined) list.push(el("option", { value: "" }, emptyLabel));
    for (const [value, label] of items) {
      list.push(el("option", { value: String(value), selected: String(value) === String(selected ?? "") }, label));
    }
    return list;
  }

  function canEdit(ctx) { return ROLE_LEVEL[ctx.meta.role] >= 2; }
  function isAdmin(ctx) { return ctx.meta.role === "admin"; }
  /* D-B-017 mirror: the assignee (or an admin) edits a ticket. */
  function canEditIssue(ctx, issue) {
    return isAdmin(ctx) || (canEdit(ctx) && issue.assignee_id === DA.session.user.id);
  }

  /* Client-side mirror of the server rule, used for drag and drop. */
  function findTransition(ctx, issue, toStatusId) {
    const type = ctx.meta.types.find((t) => t.id === issue.type_id);
    if (!type) return null;
    return ctx.meta.transitions.find((t) => t.workflow_id === type.workflow_id
      && t.to_status_id === toStatusId
      && (t.from_status_id === null || t.from_status_id === issue.status_id)
      && ROLE_LEVEL[ctx.meta.role] >= ROLE_LEVEL[t.min_role]) || null;
  }

  function relativeDate(iso) {
    if (!iso) return "";
    const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (minutes < 1) return "à l'instant";
    if (minutes < 60) return "il y a " + minutes + " min";
    if (minutes < 1440) return "il y a " + Math.round(minutes / 60) + " h";
    return DA.formatDate(iso);
  }

  /* ---------- Shell ---------- */
  /* Two shells share these screens (D-B-011): Agile (time management by
     tickets, plus Change Management) and Goldmine (requirements, own top tab). */
  const AGILE_SHELL = {
    module: "agile", title: "Agile", home: "board", issueNav: "issues",
    mark: () => el("img", { src: DA.mark("agile"), alt: "", class: "ag-mark-img" }),
    /* D-B-087: order of use -- plan the Backlog, then run the Sprint on the Board (home stays the Board) */
    nav: [["backlog", "Backlog"], ["board", "Board"], ["issues", "Tickets"], ["changes", "Change Management"],
      ["csv", "Import / Export"]],
    adminNav: [["settings", "Paramètres du Space"]],  // D-A-039: set-up, administrators only
  };

  function sidebar(ctx, active) {
    const shell = ctx.shell;
    const picker = el("select", {
      class: "ag-project-picker", "aria-label": "Space",
      onchange: (ev) => { location.hash = "#/" + shell.module + "/" + ev.target.value + "/" + active; },
    }, options(DA.session.projects.map((p) => [p.key, p.key + " · " + p.name]), ctx.key));
    return el("aside", { class: "ag-sidebar ag-shell-" + shell.module },
      el("div", { class: "ag-sidebar-mark" }, shell.mark()),
      DA.spaces.withStar(picker, ctx.key),
      el("nav", { class: "ag-nav", "aria-label": "Navigation " + shell.title },
        shell.nav.map(([view, label]) => el("a", {
          class: "ag-nav-item" + (view === active ? " active" : ""), href: href(ctx, view),
          "aria-current": view === active ? "page" : null }, label)),
        DA.adminNav(shell.adminNav || [], active, (view) => href(ctx, view))),
      DA.spaces.allLink(shell.module));  // D-B-098
  }

  function pageHead(ctx, crumbs, actions) {
    const trail = el("nav", { class: "ag-crumbs", "aria-label": "Fil d'Ariane" },
      el("a", { href: href(ctx, ctx.shell.home) }, ctx.meta.project.name),
      crumbs.flatMap((c) => [el("span", { class: "ag-crumb-sep", "aria-hidden": "true" }, "/"), c]));
    return el("div", { class: "ag-head" }, trail,
      el("div", { class: "ag-head-actions" },
        actions || null,
        canEdit(ctx) && !ctx.shell.noCreate && ctx.module !== "goldmine" ? el("button", { class: "btn btn-primary", type: "button",
          onclick: () => DA.agile.openCreate(ctx) }, "Créer un ticket") : null));
  }

  /* Project choice: same layout as inside a project, the module's logo already
     in the left panel (D-B-013), like Dynamite. */
  function projectPicker(main, shell) {
    const page = el("section", { class: "ag-page" });
    const go = (key) => "#/" + shell.module + "/" + key + "/" + shell.home;
    main.append(el("div", { class: "ag-layout" },
      el("aside", { class: "ag-sidebar ag-shell-" + shell.module }, el("div", { class: "ag-sidebar-mark" }, shell.mark()),
        DA.spaces.sidebar(shell.module, go)),  // D-B-098: second way in, and the default Space
      page));
    page.append(el("div", { class: "page-head" },
      el("h1", null, shell.title),
      el("p", { class: "muted" }, "Choisissez un Space.")));
    if (!DA.session.projects.length) {
      page.append(el("div", { class: "empty" }, el("p", null, "Aucun Space accessible.")));
      return;
    }
    page.append(el("div", { class: "project-list" }, DA.session.projects.map((p) =>
      el("a", { class: "project ag-project-card", href: "#/" + shell.module + "/" + p.key + "/" + shell.home },
        el("div", { class: "project-top" }, el("span", { class: "key" }, p.key), DA.roleBadge(p.role)),
        el("h2", null, p.name),
        el("p", { class: "muted" }, p.description || "Aucune description.")))));
  }

  function notEnabled(main, ctx) {
    main.classList.add("ag-narrow");
    const admin = ctx.meta.role === "admin";
    main.append(el("div", { class: "empty" },
      el("h2", null, "Agile n'est pas activé sur " + ctx.meta.project.name),
      el("p", { class: "muted" }, admin
        ? "L'activation crée cinq types de tickets et un workflow standard, modifiables ensuite."
        : "Demandez à un administrateur de l'activer."),
      admin ? el("button", { class: "btn btn-primary", type: "button", onclick: async () => {
        try {
          await api.post("/api/agile/p/" + ctx.pid + "/init");
          toast("Agile activé.", "success");
          render(main, [ctx.key, ctx.shell.home], ctx.shell);
        } catch (err) { toast(err.message, "error"); }
      } }, "Activer Agile") : null));
  }

  async function render(main, parts, shellArg) {
    const shell = shellArg || AGILE_SHELL;
    clear(main);
    main.classList.add("ag-main");
    const key = (parts[0] || "").toUpperCase();
    const project = DA.session.projects.find((p) => p.key === key);
    if (!project) {
      if (DA.spaces.enter(shell.module, parts, (k) => "#/" + shell.module + "/" + k + "/" + shell.home)) return;
      projectPicker(main, shell);
      return;
    }

    const ctx = { key, pid: project.id, main, view: parts[1] || shell.home, arg: parts[2], shell, module: shell.module };
    try {
      ctx.meta = await api.get("/api/agile/p/" + ctx.pid + "/meta");
    } catch (err) {
      main.append(el("p", { class: "form-error" }, err.message));
      return;
    }
    if (!ctx.meta.enabled) { notEnabled(main, ctx); return; }
    labelColors.clear();
    ctx.meta.labels.forEach((l) => labelColors.set(l.name.toLowerCase(), l.color_key));

    ctx.refresh = () => render(main, parts, shell);
    const page = el("section", { class: "ag-page" });
    const navView = ctx.view === "issue" ? shell.issueNav : ctx.view;
    main.append(el("div", { class: "ag-layout" }, sidebar(ctx, navView), page));
    const view = DA.agile.views[ctx.view] || DA.agile.views[shell.home];
    try {
      await view(page, ctx);
    } catch (err) {
      page.append(el("p", { class: "form-error" }, err.message));
      if (err.status !== 401) console.error(err);
    }
  }

  DA.agile = {
    views: {},
    PRIORITY, CATEGORY_LABELS, LINK_LABELS,
    typeIcon, priorityIcon, statusBadge, labelChip, avatar, issueLink, richText, options,
    canEdit, canEditIssue, isAdmin, findTransition, relativeDate, pageHead, roadmapIcon, href, render, staticSvg,
    openCreate: () => toast("Écran de création non chargé.", "error"),
  };
  DA.registerModule("agile", render);
})();
