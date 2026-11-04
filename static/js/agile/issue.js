/* Agile - ticket screens: creation dialog and two-panel ticket page. */
(function () {
  "use strict";

  const { api, el, clear, field, toast, modal } = DA;
  const A = DA.agile;

  function base(ctx) { return "/api/agile/p/" + ctx.pid; }

  function memberOptions(ctx, selected) {
    return A.options(ctx.meta.members.map((m) => [m.id, m.display_name]), selected, "Non assigné");
  }
  function sprintOptions(ctx, selected) {
    const open = ctx.meta.sprints.filter((s) => s.state !== "closed" || String(s.id) === String(selected));
    return A.options(open.map((s) => [s.id, s.name + (s.state === "active" ? " (actif)" : "")]), selected, "Backlog");
  }
  function versionOptions(ctx, selected) {
    return A.options(ctx.meta.versions.map((v) => [v.id, v.name]), selected, "Aucune");
  }
  function priorityOptions(selected) {
    return A.options(Object.entries(A.PRIORITY).map(([k, p]) => [k, p.label]), selected);
  }

  /* ---------- Labels editor (chips + free input with suggestions) ---------- */
  function labelEditor(ctx, initial, onChange) {
    let labels = initial.slice();
    const listId = "ag-labels-" + Math.random().toString(36).slice(2);
    const chips = el("span", { class: "ag-chips" });
    const input = el("input", { type: "text", list: listId, maxlength: 40, class: "ag-chip-input",
      placeholder: "Ajouter…", "aria-label": "Ajouter un label" });
    const datalist = el("datalist", { id: listId },
      ctx.meta.labels.map((l) => el("option", { value: l.name })));

    function draw() {
      clear(chips);
      labels.forEach((name) => chips.append(el("span", { class: "ag-label ag-label-edit" }, name,
        el("button", { type: "button", class: "ag-chip-x", "aria-label": "Retirer " + name,
          onclick: () => { labels = labels.filter((l) => l !== name); draw(); onChange(labels); } }, "×"))));
    }
    function add() {
      const name = input.value.trim().replace(/\s+/g, "-");
      input.value = "";
      if (!name || labels.some((l) => l.toLowerCase() === name.toLowerCase())) return;
      labels.push(name);
      draw();
      onChange(labels);
    }
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === ",") { ev.preventDefault(); add(); }
    });
    input.addEventListener("change", add);
    draw();
    return el("div", { class: "ag-label-editor" }, chips, input, datalist);
  }

  /* ---------- Create dialog ---------- */
  function openCreate(ctx, preset) {
    preset = preset || {};
    // Agile creates Agile work only; Goldmine and Change Management pass their own types (D-B-011).
    const pool = preset.types ? ctx.meta.types.filter((t) => preset.types.includes(t.id))
      : ctx.meta.types.filter((t) => t.bucket === "agile");
    const types = pool.filter((t) => (preset.parentNumber ? true : !t.is_subtask));
    const defaultType = preset.typeId || (types.find((t) => t.icon_key === "task") || types[0]).id;
    const type = el("select", { required: true }, A.options(types.map((t) => [t.id, t.name]), defaultType));
    const title = el("input", { type: "text", maxlength: 255, required: true });
    const description = el("textarea", { rows: 5, maxlength: 20000 });
    const priority = el("select", null, priorityOptions("medium"));
    const assignee = el("select", null, memberOptions(ctx, ""));
    const parent = el("input", { type: "text", inputmode: "numeric", placeholder: "n° d'epic ou de ticket",
      value: preset.parentNumber || "" });
    const sprint = el("select", null, sprintOptions(ctx, preset.sprintId || ""));
    const version = el("select", null, versionOptions(ctx, ""));
    const points = el("input", { type: "text", inputmode: "decimal", maxlength: 6 });
    const due = el("input", { type: "date" });
    let labels = [];
    const error = el("p", { class: "form-error", role: "alert" });
    const submit = el("button", { type: "submit", class: "btn btn-primary" }, "Créer le ticket");
    let close = null;

    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      error.textContent = "";
      submit.disabled = true;
      try {
        const created = await api.post(base(ctx) + "/issues", {
          type_id: Number(type.value), title: title.value, description: description.value,
          priority: priority.value, assignee_id: assignee.value || null,
          parent_number: parent.value.trim() || null, sprint_id: sprint.value || null,
          version_id: version.value || null, story_points: points.value.trim() || null,
          due_date: due.value || null, labels,
        });
        close();
        toast(created.key + " créé.", "success");
        if (preset.onCreated) preset.onCreated(created);
        else location.hash = A.href(ctx, "issue/" + created.number);
      } catch (err) {
        error.textContent = err.message;
      } finally {
        submit.disabled = false;
      }
    } },
      el("div", { class: "form-row" }, field("Type", type), field("Parent", parent)),
      field("Title", title),
      field("Description", description),
      el("div", { class: "form-row" }, field("Priority", priority), field("Assignee", assignee)),
      field("Labels", labelEditor(ctx, [], (l) => { labels = l; }), "Entrée pour valider, sans espace"),
      el("div", { class: "form-row" }, field("Sprint", sprint), field("Version", version)),
      el("div", { class: "form-row" }, field("Points", points), field("Due Date", due)),
      error,
      el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"), submit));

    close = modal("Créer un ticket", form);
    const dialogs = document.querySelectorAll(".modal");
    dialogs[dialogs.length - 1].classList.add("modal-wide");
    title.focus();
  }
  A.openCreate = openCreate;

  /* ---------- Ticket page ---------- */
  async function issueView(page, ctx) {
    const number = Number(ctx.arg);
    const data = await api.get(base(ctx) + "/issues/" + number);
    const issue = data.issue;
    // D-B-017: content is edited by the assignee (or an admin); members comment.
    const editable = issue.can_edit;
    const url = base(ctx) + "/issues/" + number;
    const reload = () => issueView(clearPage(page), ctx);

    async function save(body) {
      try {
        await api.patch(url, body);
        reload();
      } catch (err) { toast(err.message, "error"); reload(); }
    }

    // D-B-011: a requirement opens in the Goldmine tab, anything else in Agile,
    // whichever link led here (ticket block, cross-project link, CSV report…).
    const home = issue.is_requirement ? "goldmine" : "agile";
    if ((ctx.module || "agile") !== home) {
      location.replace("#/" + home + "/" + ctx.key + "/issue/" + number);
      return;
    }
    const section = issue.is_requirement ? ["goldmine", "Requirements"]
      : (issue.change_role ? ["changes", "Change Management"] : ["issues", "Tickets"]);
    const crumbs = [el("a", { href: A.href(ctx, section[0]) }, section[1])];
    document.querySelectorAll(".ag-nav-item").forEach((a) => {
      const on = a.getAttribute("href") === A.href(ctx, section[0]);
      a.classList.toggle("active", on);
      if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    if (issue.parent) crumbs.push(A.issueLink(ctx, issue.parent));
    crumbs.push(el("span", { class: "ag-key" }, issue.key));
    page.append(A.pageHead(ctx, crumbs));
    if (!editable && A.canEdit(ctx)) page.append(ownerNotice(issue, url, reload));

    page.append(el("div", { class: "ag-issue" },
      mainColumn(ctx, issue, editable, url, save, reload),
      sideColumn(ctx, issue, editable, url, save, reload)));
  }

  function clearPage(page) { clear(page); return page; }

  function ownerNotice(issue, url, reload) {
    const take = async () => {
      try {
        await api.patch(url, { assignee_id: DA.session.user.id });
        toast(issue.key + " vous est attribué.", "success");
        reload();
      } catch (err) { toast(err.message, "error"); }
    };
    return el("div", { class: "ag-owner-notice", role: "note" },
      el("span", null, issue.can_take
        ? "Ce ticket n'est attribué à personne : prenez-le pour le modifier. Vous pouvez déjà le commenter."
        : "Lecture seule : seul " + (issue.assignee_name || "son responsable")
          + " (ou un administrateur) modifie ce ticket. Vous pouvez le commenter."),
      issue.can_take ? el("button", { type: "button", class: "btn btn-primary btn-small", onclick: take },
        "Prendre le ticket") : null);
  }

  function editableTitle(issue, editable, save) {
    const heading = el("h1", { class: "ag-issue-title" }, issue.title);
    if (!editable) return heading;
    heading.tabIndex = 0;
    heading.title = "Cliquer pour modifier";
    const startEdit = () => {
      const input = el("input", { type: "text", value: issue.title, maxlength: 255, class: "ag-title-input" });
      const done = () => { if (input.value.trim() && input.value !== issue.title) save({ title: input.value }); else input.replaceWith(heading); };
      input.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter") done();
        if (ev.key === "Escape") input.replaceWith(heading);
      });
      input.addEventListener("blur", done);
      heading.replaceWith(input);
      input.focus();
    };
    heading.addEventListener("click", startEdit);
    heading.addEventListener("keydown", (ev) => { if (ev.key === "Enter") startEdit(); });
    return heading;
  }

  function descriptionBlock(issue, editable, save) {
    const box = el("div", { class: "ag-block" });
    function show() {
      clear(box);
      box.append(el("div", { class: "ag-block-head" }, el("h2", null, "Description"),
        editable ? el("button", { type: "button", class: "link-btn", onclick: edit }, "Modifier") : null),
      issue.description ? A.richText(issue.description) : el("p", { class: "muted" }, "Aucune description."));
    }
    function edit() {
      clear(box);
      const area = el("textarea", { rows: 8, maxlength: 20000 });
      area.value = issue.description || "";
      box.append(el("h2", null, "Description"), area, el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn", onclick: show }, "Annuler"),
        el("button", { type: "button", class: "btn btn-primary",
          onclick: () => save({ description: area.value }) }, "Enregistrer")));
      area.focus();
    }
    show();
    return box;
  }

  function childrenBlock(ctx, issue, editable, reload) {
    const ecnTask = issue.change_role === "ecn" && issue.ecn_task_type_id;
    const subtype = ecnTask ? ctx.meta.types.find((t) => t.id === issue.ecn_task_type_id)
      : ctx.meta.types.find((t) => t.is_subtask && t.bucket === "agile");
    return el("div", { class: "ag-block" },
      el("div", { class: "ag-block-head" }, el("h2", null, "Sous-tickets"),
        editable ? el("button", { type: "button", class: "link-btn", onclick: () => openCreate(ctx, {
          parentNumber: issue.number, typeId: subtype ? subtype.id : null, onCreated: reload,
          types: ecnTask ? [issue.ecn_task_type_id] : null }) },
        "Ajouter") : null),
      issue.children.length
        ? el("ul", { class: "ag-rows" }, issue.children.map((child) => el("li", { class: "ag-row" },
          A.typeIcon(child.icon_key, child.type_name), A.issueLink(ctx, child),
          el("span", { class: "ag-row-title" }, child.title),
          A.statusBadge(child.status_name, child.status_category))))
        : el("p", { class: "muted" }, "Aucun."));
  }

  const A_ISSUE_LINK_LABEL = { blocks: "bloque", relates: "est lié à", duplicates: "duplique",
    implements: "implémente" };

  function linkRow(ctx, link, editable, url, reload) {
    const target = el("a", { class: "ag-key", href: "#/agile/" + link.project_key + "/issue/" + link.number },
      link.key);
    return el("li", { class: "ag-row" },
      el("span", { class: "ag-link-type" }, A.LINK_LABELS[link.link_type][link.direction]),
      target, el("span", { class: "ag-row-title" }, link.title),
      A.statusBadge(link.status_name, link.status_category),
      editable ? el("button", { type: "button", class: "icon-btn", "aria-label": "Supprimer le lien",
        onclick: async () => {
          try { await api.del(url + "/links/" + link.id); reload(); } catch (err) { toast(err.message, "error"); }
        } }, "×") : null);
  }

  function linksBlock(ctx, issue, editable, url, reload) {
    // "implements" links into this issue are already shown in "Implémenté
    // par" when this is a requirement; avoid listing them twice.
    const visible = issue.links.filter((l) => !(issue.is_requirement && l.link_type === "implements" && l.direction === "in")
      && !(issue.change_role && l.link_type === "resolves"));  // shown in the change block instead
    const block = el("div", { class: "ag-block" }, el("h2", null, "Links"));
    if (visible.length) {
      block.append(el("ul", { class: "ag-rows" },
        visible.map((link) => linkRow(ctx, link, editable, url, reload))));
    } else {
      block.append(el("p", { class: "muted" }, "Aucun."));
    }
    if (editable) {
      const type = el("select", { "aria-label": "Type de lien" },
        A.options([["blocks", "bloque"], ["relates", "est lié à"], ["duplicates", "duplique"],
          ["implements", "implémente (requirement)"], ["resolves", "traite (ECN → PR / bug)"]], "relates"));
      const target = el("input", { type: "text", placeholder: "clé, ex. EQP-4 ou REQ-12",
        "aria-label": "Key du ticket lié", class: "ag-key-input" });
      block.append(el("form", { class: "ag-inline-form", onsubmit: async (ev) => {
        ev.preventDefault();
        try {
          await api.post(url + "/links", { link_type: type.value, target_key: target.value.trim() });
          reload();
        } catch (err) { toast(err.message, "error"); }
      } }, type, target, el("button", { type: "submit", class: "btn btn-small" }, "Lier")));
    }
    return block;
  }

  function implementedByBlock(ctx, issue) {
    if (!issue.is_requirement) return null;
    return el("div", { class: "ag-block" },
      el("h2", null, "Implémenté par"),
      issue.implemented_by.length
        ? el("ul", { class: "ag-rows" }, issue.implemented_by.map((t) => el("li", { class: "ag-row" },
          el("a", { class: "ag-key", href: "#/agile/" + t.project_key + "/issue/" + t.number }, t.key),
          el("span", { class: "ag-row-title" }, t.title),
          A.statusBadge(t.status_name, t.status_category))))
        : el("p", { class: "muted" }, "Aucun ticket ne l'implémente pour l'instant."));
  }

  function activityBlock(ctx, issue, editable, url, reload) {
    const commentable = A.canEdit(ctx);
    const body = el("div");
    const tabs = el("div", { class: "subtabs", role: "tablist" });
    function tab(label, drawFn, active) {
      const button = el("button", { type: "button", role: "tab", class: "subtab ag-tab" + (active ? " active" : ""),
        "aria-selected": active ? "true" : "false", onclick: () => {
          tabs.querySelectorAll(".ag-tab").forEach((b) => { b.classList.remove("active"); b.setAttribute("aria-selected", "false"); });
          button.classList.add("active");
          button.setAttribute("aria-selected", "true");
          drawFn();
        } }, label);
      return button;
    }
    function commentNode(cm, depth) {
      const canDelete = (!cm.external_author && cm.author_id === DA.session.user.id) || A.isAdmin(ctx);
      const node = el("article", { class: "ag-comment" },
        el("div", { class: "ag-comment-head" }, A.avatar(cm.author_name),
          el("strong", null, cm.author_name || "Ancien compte"),
          cm.is_question ? el("span", { class: "badge badge-warn" }, "Question") : null,
          cm.external_author ? el("span", { class: "badge badge-neutral" }, "Externe") : null,
          cm.requirement_ref ? el("span", { class: "ag-key" }, cm.requirement_ref) : null,
          el("span", { class: "muted" }, A.relativeDate(cm.created_at)),
          commentable ? el("button", { type: "button", class: "link-btn", onclick: () => reply(cm) }, "Répondre") : null,
          editable && A.promoteComment ? el("button", { type: "button", class: "link-btn",
            title: "Reprendre ce commentaire dans la synthèse client",
            onclick: () => A.promoteComment(issue, cm, url, reload) }, "→ Synthèse") : null,
          canDelete ? el("button", { type: "button", class: "link-btn", onclick: async () => {
            try { await api.del(url + "/comments/" + cm.id); reload(); } catch (err) { toast(err.message, "error"); }
          } }, "Supprimer") : null),
        A.richText(cm.body));
      node.classList.add("ag-comment-depth-" + Math.min(depth, 3));
      return node;
    }
    function reply(parent) {
      const existing = document.getElementById("ag-reply-form");
      if (existing) existing.remove();
      const area = el("textarea", { rows: 2, maxlength: 10000, placeholder: "Répondre…", "aria-label": "Réponse" });
      const form = el("form", { id: "ag-reply-form", class: "ag-comment-form ag-reply-form", onsubmit: async (ev) => {
        ev.preventDefault();
        if (!area.value.trim()) return;
        try {
          await api.post(url + "/comments", { body: area.value, parent_comment_id: parent.id });
          reload();
        } catch (err) { toast(err.message, "error"); }
      } }, area, el("div", { class: "form-actions" },
        el("button", { type: "submit", class: "btn btn-primary btn-small" }, "Répondre")));
      form.classList.add("ag-comment-depth-1");
      area.focus();
      const parentNode = commentNodes.get(parent.id);
      if (parentNode) parentNode.after(form);
      else body.append(form);
    }
    let commentNodes;
    function comments() {
      clear(body);
      commentNodes = new Map();
      const byParent = new Map();
      issue.comments.forEach((cm) => {
        const key = cm.parent_comment_id || 0;
        if (!byParent.has(key)) byParent.set(key, []);
        byParent.get(key).push(cm);
      });
      (function walk(parentId, depth) {
        (byParent.get(parentId) || []).forEach((cm) => {
          const node = commentNode(cm, depth);
          commentNodes.set(cm.id, node);
          body.append(node);
          walk(cm.id, depth + 1);
        });
      })(0, 0);
      if (!issue.comments.length) body.append(el("p", { class: "muted" }, "Aucun commentaire."));
      if (commentable) {
        const area = el("textarea", { rows: 3, maxlength: 10000, placeholder: "Ajouter un commentaire…",
          "aria-label": "Nouveau commentaire" });
        const question = el("label", { class: "check" },
          el("input", { type: "checkbox", id: "ag-new-question" }), "Question");
        const ref = el("input", { type: "text", maxlength: 40, placeholder: "réf. requirement (optionnel)",
          "aria-label": "Référence de requirement externe", class: "ag-small-input" });
        body.append(el("form", { class: "ag-comment-form", onsubmit: async (ev) => {
          ev.preventDefault();
          if (!area.value.trim()) return;
          try {
            await api.post(url + "/comments", { body: area.value,
              is_question: question.firstChild.checked, requirement_ref: ref.value.trim() });
            reload();
          } catch (err) { toast(err.message, "error"); }
        } }, area, el("div", { class: "form-row" }, question, ref),
        el("div", { class: "form-actions" },
          el("button", { type: "submit", class: "btn btn-primary btn-small" }, "Commenter"))));
      }
    }
    function history() {
      clear(body);
      body.append(el("ul", { class: "ag-history" }, issue.history.map((h) => el("li", null,
        el("strong", null, h.user_name || "Système"), " ",
        h.field === "created" ? "a créé le ticket" : ["a modifié ", el("em", null, fieldLabel(h.field)), " : ",
          el("span", { class: "muted" }, h.old_value ?? "vide"), " → ", h.new_value ?? "vide"],
        el("span", { class: "muted ag-history-date" }, " · " + A.relativeDate(h.ts))))));
    }
    tabs.append(tab("Commentaires (" + issue.comments.length + ")", comments, true), tab("History", history, false));
    comments();
    return el("div", { class: "ag-block" }, tabs, body);
  }

  const FIELD_LABELS = { title: "titre", description: "description", priority: "priority",
    assignee_id: "assigné", parent_id: "parent", sprint_id: "sprint", version_id: "version",
    story_points: "points", due_date: "échéance", type_id: "type", status: "status", labels: "labels",
    client_summary: "synthèse client" };
  function fieldLabel(name) { return FIELD_LABELS[name] || name; }

  function mainColumn(ctx, issue, editable, url, save, reload) {
    return el("div", { class: "ag-issue-main" },
      el("div", { class: "ag-issue-kicker" }, A.typeIcon(issue.icon_key, issue.type_name),
        el("span", { class: "ag-key" }, issue.key),
        issue.is_requirement ? el("span", { class: "badge badge-admin" }, "Requirement") : null),
      editableTitle(issue, editable, save),
      descriptionBlock(issue, editable, save),
      A.summaryBlock ? A.summaryBlock(ctx, issue, editable, url, reload) : null,
      A.requirementBlock ? A.requirementBlock(ctx, issue, editable, reload) : null,
      A.qaPanel ? A.qaPanel(ctx, issue) : null,  // D-B-037
      A.changeBlock && issue.change_role ? A.changeBlock(ctx, issue, editable, reload) : null,
      implementedByBlock(ctx, issue),
      childrenBlock(ctx, issue, editable, reload),
      linksBlock(ctx, issue, editable, url, reload),
      activityBlock(ctx, issue, editable, url, reload));
  }

  function sideColumn(ctx, issue, editable, url, save, reload) {
    const transition = el("select", { class: "ag-transition", "aria-label": "Changer de status",
      disabled: !editable || !issue.transitions.length },
    el("option", { value: "" }, issue.status_name + (issue.transitions.length ? " ▾" : "")),
    issue.transitions.map((t) => el("option", { value: t.id }, t.name + " → " + t.to_name)));
    transition.classList.add("ag-status-" + issue.status_category);
    transition.addEventListener("change", async () => {
      if (!transition.value) return;
      try {
        await api.post(url + "/transition", { transition_id: Number(transition.value) });
        reload();
      } catch (err) { toast(err.message, "error"); reload(); }
    });

    function selectRow(label, name, opts) {
      const select = el("select", { disabled: !editable, "aria-label": label }, opts);
      select.addEventListener("change", () => save({ [name]: select.value || null }));
      return row(label, select);
    }
    function inputRow(label, name, value, attrs) {
      const input = el("input", Object.assign({ value: value ?? "", disabled: !editable, "aria-label": label }, attrs));
      input.addEventListener("change", () => save({ [name]: input.value.trim() || null }));
      return row(label, input);
    }
    function row(label, control) {
      return el("div", { class: "ag-field" }, el("span", { class: "ag-field-label" }, label), control);
    }

    const sameWorkflow = ctx.meta.types.filter((t) => t.workflow_id ===
      (ctx.meta.types.find((x) => x.id === issue.type_id) || {}).workflow_id);
    const labels = editable
      ? labelEditor(ctx, issue.labels, async (list) => {
        try { await api.put(url + "/labels", { labels: list }); } catch (err) { toast(err.message, "error"); reload(); }
      })
      : el("span", { class: "ag-chips" }, issue.labels.map(A.labelChip));

    return el("aside", { class: "ag-issue-side" },
      transition,
      el("div", { class: "ag-fields" },
        selectRow("Assignee", "assignee_id", memberOptions(ctx, issue.assignee_id)),
        row("Reporter", el("span", null, issue.reporter_name || "—")),
        selectRow("Priority", "priority", priorityOptions(issue.priority)),
        selectRow("Type", "type_id", A.options(sameWorkflow.map((t) => [t.id, t.name]), issue.type_id)),
        row("Labels", labels),
        selectRow("Sprint", "sprint_id", sprintOptions(ctx, issue.sprint_id)),
        selectRow("Version", "version_id", versionOptions(ctx, issue.version_id)),
        inputRow("Points", "story_points", issue.story_points, { type: "text", inputmode: "decimal", maxlength: 6 }),
        inputRow("Due Date", "due_date", issue.due_date, { type: "date" }),
        inputRow("Parent", "parent_number", issue.parent ? issue.parent.number : "",
          { type: "text", inputmode: "numeric", placeholder: "n°" })),
      el("dl", { class: "ag-dates" },
        el("dt", null, "Créé"), el("dd", null, DA.formatDate(issue.created_at)),
        el("dt", null, "Modifié"), el("dd", null, DA.formatDate(issue.updated_at)),
        issue.resolved_at ? [el("dt", null, "Résolu"), el("dd", null, DA.formatDate(issue.resolved_at))] : null),
      A.isAdmin(ctx) ? el("button", { type: "button", class: "btn btn-danger btn-small", onclick: async () => {
        if (!window.confirm("Supprimer définitivement " + issue.key + " ?")) return;
        try {
          await api.del(url);
          toast(issue.key + " supprimé.", "success");
          location.hash = A.href(ctx, issue.is_requirement ? "goldmine" : (issue.change_role ? "changes" : "issues"));
        } catch (err) { toast(err.message, "error"); }
      } }, "Supprimer le ticket") : null);
  }

  A.views.issue = issueView;
})();
