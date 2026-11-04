/* Agile - project settings: workflows (statuses, transitions), types,
   labels, versions. Configuration is reserved to administrators (H1);
   versions can be managed by editors. */
(function () {
  "use strict";

  const { api, el, toast } = DA;
  const A = DA.agile;

  const CATEGORIES = [["todo", "To Do"], ["in_progress", "In Progress"], ["done", "Done"]];
  const ICONS = [["epic", "Epic ⚡"], ["story", "Story ▮"], ["task", "Task ✓"], ["bug", "Bug ●"], ["subtask", "Sub-task ↳"], ["requirement", "Requirement §"], ["ecn", "ECN Δ"]];
  const COLORS = [["neutral", "Gris"], ["blue", "Bleu"], ["green", "Vert"], ["amber", "Ambre"], ["red", "Rouge"], ["violet", "Violet"]];

  function base(ctx) { return "/api/agile/p/" + ctx.pid; }

  async function run(ctx, promise, message) {
    try {
      await promise;
      if (message) toast(message, "success");
      ctx.refresh();
    } catch (err) { toast(err.message, "error"); }
  }

  function selectFor(items, value, onChange, attrs) {
    const select = el("select", attrs || null, A.options(items, value));
    select.addEventListener("change", () => onChange(select.value));
    return select;
  }

  function deleteButton(label, action) {
    return el("button", { type: "button", class: "btn btn-small btn-danger", onclick: action }, label || "Supprimer");
  }

  /* ---------- Workflows ---------- */
  function workflowPanel(ctx, wf, admin) {
    const statuses = ctx.meta.statuses.filter((s) => s.workflow_id === wf.id);
    const transitions = ctx.meta.transitions.filter((t) => t.workflow_id === wf.id);
    const statusName = (id) => (id === null ? "N'importe quel status" : (statuses.find((s) => s.id === id) || {}).name);
    const usedBy = ctx.meta.types.filter((t) => t.workflow_id === wf.id).map((t) => t.name).join(", ") || "aucun type";

    const statusTable = DA.table(["Status", "Category", "Initial", ""], statuses.map((s) => el("tr", null,
      el("td", null, admin ? renameInput(s.name, (v) => run(ctx, api.patch(base(ctx) + "/statuses/" + s.id, { name: v })))
        : A.statusBadge(s.name, s.category)),
      el("td", null, admin ? selectFor(CATEGORIES, s.category,
        (v) => run(ctx, api.patch(base(ctx) + "/statuses/" + s.id, { category: v })), { "aria-label": "Category de " + s.name })
        : A.CATEGORY_LABELS[s.category]),
      el("td", null, s.is_initial ? el("span", { class: "badge badge-ok" }, "Initial")
        : admin ? el("button", { type: "button", class: "link-btn", onclick: () =>
          run(ctx, api.patch(base(ctx) + "/statuses/" + s.id, { is_initial: true })) }, "Définir") : ""),
      el("td", null, admin && !s.is_initial ? deleteButton(null, () =>
        run(ctx, api.del(base(ctx) + "/statuses/" + s.id), "Status supprimé.")) : null))));

    const transitionTable = DA.table(["Nom", "De", "Vers", "Rôle minimal", ""], transitions.map((t) => el("tr", null,
      el("td", null, t.name), el("td", null, statusName(t.from_status_id)), el("td", null, statusName(t.to_status_id)),
      el("td", null, t.min_role === "admin" ? "Admin" : "Éditeur"),
      el("td", null, admin ? deleteButton(null, () => run(ctx, api.del(base(ctx) + "/transitions/" + t.id))) : null))));

    const panel = el("section", { class: "panel ag-settings-panel" },
      el("div", { class: "ag-block-head" }, el("h2", null, wf.name + (wf.is_default ? " (par défaut)" : "")),
        el("span", { class: "muted" }, "Utilisé par : " + usedBy)),
      el("h3", null, "Statuses"), statusTable);
    if (admin) panel.append(addStatusForm(ctx, wf));
    panel.append(el("h3", null, "Transitions"),
      el("p", { class: "muted ag-sub" }, "Un ticket ne change de status que par une transition listée ici."),
      transitionTable);
    if (admin) panel.append(addTransitionForm(ctx, wf, statuses));
    return panel;
  }

  function renameInput(value, onSave) {
    const input = el("input", { type: "text", value, maxlength: 60, class: "ag-inline-input", "aria-label": "Nom" });
    input.addEventListener("change", () => { if (input.value.trim()) onSave(input.value.trim()); });
    return input;
  }

  function addStatusForm(ctx, wf) {
    const name = el("input", { type: "text", maxlength: 40, required: true, placeholder: "Nouveau status" });
    const category = el("select", null, A.options(CATEGORIES, "in_progress"));
    return el("form", { class: "ag-inline-form", onsubmit: (ev) => {
      ev.preventDefault();
      run(ctx, api.post(base(ctx) + "/statuses", { workflow_id: wf.id, name: name.value, category: category.value }),
        "Status ajouté.");
    } }, name, category, el("button", { type: "submit", class: "btn btn-small" }, "Ajouter le status"));
  }

  function addTransitionForm(ctx, wf, statuses) {
    const items = statuses.map((s) => [s.id, s.name]);
    const from = el("select", { "aria-label": "Depuis" }, A.options(items, "", "N'importe quel status"));
    const to = el("select", { "aria-label": "Vers", required: true }, A.options(items, items.length ? items[0][0] : ""));
    const name = el("input", { type: "text", maxlength: 60, placeholder: "Nom (ex. Valider)" });
    const role = el("select", { "aria-label": "Rôle minimal" }, A.options([["editor", "Éditeur"], ["admin", "Admin"]], "editor"));
    return el("form", { class: "ag-inline-form", onsubmit: (ev) => {
      ev.preventDefault();
      run(ctx, api.post(base(ctx) + "/transitions", { workflow_id: wf.id, from_status_id: from.value || null,
        to_status_id: Number(to.value), name: name.value, min_role: role.value }), "Transition ajoutée.");
    } }, from, el("span", { class: "muted" }, "→"), to, name, role,
    el("button", { type: "submit", class: "btn btn-small" }, "Ajouter la transition"));
  }

  /* ---------- Types ---------- */
  function typesPanel(ctx, admin) {
    const workflows = ctx.meta.workflows.map((w) => [w.id, w.name]);
    const rows = ctx.meta.types.map((t) => el("tr", null,
      el("td", null, A.typeIcon(t.icon_key, t.name)),
      el("td", null, admin ? renameInput(t.name, (v) => run(ctx, api.patch(base(ctx) + "/types/" + t.id, { name: v }))) : t.name),
      el("td", null, admin ? selectFor(ICONS, t.icon_key, (v) => run(ctx, api.patch(base(ctx) + "/types/" + t.id, { icon_key: v })),
        { "aria-label": "Icône" }) : ""),
      el("td", null, admin ? selectFor(workflows, t.workflow_id, (v) => run(ctx, api.patch(base(ctx) + "/types/" + t.id,
        { workflow_id: Number(v) })), { "aria-label": "Workflow" }) : (workflows.find((w) => w[0] === t.workflow_id) || [0, ""])[1]),
      el("td", null, t.is_subtask ? "Sous-ticket" : admin ? (() => {
        const box = el("input", { type: "checkbox", checked: Boolean(t.is_requirement), "aria-label": "Requirement" });
        box.addEventListener("change", () => run(ctx, api.patch(base(ctx) + "/types/" + t.id,
          { is_requirement: box.checked })));
        return box;
      })() : (t.is_requirement ? "Requirement" : ""))));
    const panel = el("section", { class: "panel ag-settings-panel" }, el("h2", null, "Types de tickets"),
      el("p", { class: "muted ag-sub" }, "Un type « Requirement » peut être ciblé par un lien « implémente » "
        + "depuis n'importe quel autre projet."),
      DA.table(["", "Nom", "Icône", "Workflow", "Rôle spécial"], rows));
    if (admin) {
      const name = el("input", { type: "text", maxlength: 40, required: true, placeholder: "Nouveau type" });
      const icon = el("select", { "aria-label": "Icône" }, A.options(ICONS, "task"));
      const wf = el("select", { "aria-label": "Workflow" }, A.options(workflows, workflows[0][0]));
      panel.append(el("form", { class: "ag-inline-form", onsubmit: (ev) => {
        ev.preventDefault();
        run(ctx, api.post(base(ctx) + "/types", { name: name.value, icon_key: icon.value, workflow_id: Number(wf.value) }),
          "Type ajouté.");
      } }, name, icon, wf, el("button", { type: "submit", class: "btn btn-small" }, "Ajouter le type")));
    }
    return panel;
  }

  /* ---------- Labels and versions ---------- */
  function labelsPanel(ctx, admin) {
    return el("section", { class: "panel ag-settings-panel" }, el("h2", null, "Labels"),
      el("p", { class: "muted ag-sub" }, "Les labels se créent depuis la fiche d'un ticket. Ici : renommer, colorer, supprimer."),
      DA.table(["Label", "Couleur", "Tickets", ""], ctx.meta.labels.map((l) => el("tr", null,
        el("td", null, admin ? renameInput(l.name, (v) => run(ctx, api.patch(base(ctx) + "/labels/" + l.id, { name: v })))
          : A.labelChip(l.name)),
        el("td", null, admin ? selectFor(COLORS, l.color_key, (v) => run(ctx, api.patch(base(ctx) + "/labels/" + l.id,
          { color_key: v })), { "aria-label": "Couleur" }) : ""),
        el("td", null, String(l.uses)),
        el("td", null, admin ? deleteButton(null, () => {
          if (l.uses && !window.confirm("Retirer « " + l.name + " » de " + l.uses + " ticket(s) ?")) return;
          run(ctx, api.del(base(ctx) + "/labels/" + l.id), "Label supprimé.");
        }) : null)))));
  }

  function versionsPanel(ctx) {
    const editable = A.canEdit(ctx);
    const panel = el("section", { class: "panel ag-settings-panel" }, el("h2", null, "Versions"),
      DA.table(["Version", "Date de livraison", "Livrée", ""], ctx.meta.versions.map((v) => el("tr", null,
        el("td", null, v.name),
        el("td", null, v.release_date || el("span", { class: "muted" }, "—")),
        el("td", null, editable ? (() => {
          const box = el("input", { type: "checkbox", checked: Boolean(v.is_released), "aria-label": "Livrée" });
          box.addEventListener("change", () => run(ctx, api.patch(base(ctx) + "/versions/" + v.id, { is_released: box.checked })));
          return box;
        })() : (v.is_released ? "Oui" : "Non")),
        el("td", null, A.isAdmin(ctx) ? deleteButton(null, () => run(ctx, api.del(base(ctx) + "/versions/" + v.id))) : null)))));
    if (editable) {
      const name = el("input", { type: "text", maxlength: 60, required: true, placeholder: "ex. v0.3" });
      const date = el("input", { type: "date", "aria-label": "Date de livraison" });
      panel.append(el("form", { class: "ag-inline-form", onsubmit: (ev) => {
        ev.preventDefault();
        run(ctx, api.post(base(ctx) + "/versions", { name: name.value, release_date: date.value || null }), "Version ajoutée.");
      } }, name, date, el("button", { type: "submit", class: "btn btn-small" }, "Ajouter la version")));
    }
    return panel;
  }

  function settingsView(page, ctx) {
    const admin = A.isAdmin(ctx);
    page.append(A.pageHead(ctx, [el("span", null, "Paramètres")]));
    if (!admin) page.append(el("p", { class: "muted ag-sub" }, "Lecture seule : la configuration est réservée aux administrateurs."));
    ctx.meta.workflows.forEach((wf) => page.append(workflowPanel(ctx, wf, admin)));
    if (admin) {
      const name = el("input", { type: "text", maxlength: 60, required: true, placeholder: "Nom du nouveau workflow" });
      page.append(el("form", { class: "ag-inline-form ag-new-workflow", onsubmit: (ev) => {
        ev.preventDefault();
        run(ctx, api.post(base(ctx) + "/workflows", { name: name.value }), "Workflow créé.");
      } }, name, el("button", { type: "submit", class: "btn btn-small" }, "Créer un workflow")));
    }
    page.append(typesPanel(ctx, admin), labelsPanel(ctx, admin), versionsPanel(ctx));
  }

  A.views.settings = settingsView;
})();
