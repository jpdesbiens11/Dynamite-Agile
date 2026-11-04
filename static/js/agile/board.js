/* Agile - board (drag and drop between statuses), backlog and ticket list. */
(function () {
  "use strict";

  const { api, el, clear, field, toast, modal } = DA;
  const A = DA.agile;

  function base(ctx) { return "/api/agile/p/" + ctx.pid; }
  function prefix(ctx) { return ctx.key; }

  /* Columns: statuses of the default workflow first, then any other status. */
  function columns(ctx) {
    return ctx.meta.statuses.slice();
  }

  /* ---------- CSV import/export (H16-H20) ---------- */
  function downloadUrl(ctx, kind) { return base(ctx) + "/export/" + kind; }

  function triggerDownload(url) {
    // A same-origin navigation carries the session cookie; the server sets
    // Content-Disposition so the browser saves rather than displays it.
    // No inline style attribute (the CSP forbids style-src 'unsafe-inline'):
    // the CSS class does the hiding instead.
    const frame = el("iframe", { src: url, class: "ag-hidden-frame" });
    document.body.append(frame);
    setTimeout(() => frame.remove(), 15000);
  }

  const STATUS_CLASS = { "créée": "ok", "mise à jour": "ok", "ajoutée": "ok", "refusée": "danger", "ignorée": "neutral",
    "inchangée": "neutral" };

  /* Import report (D-A-030): each refused line says what is wrong and how
     to fix it, with its Excel row number so it can be found at once. */
  function importReportModal(result, encodingNote) {
    const report = result.report || [];
    const counts = report.reduce((acc, r) => { acc[r.status] = (acc[r.status] || 0) + 1; return acc; }, {});
    const refused = counts["refusée"] || 0;
    const warnings = report.filter((r) => r.warning).length;
    const chips = Object.entries(counts).map(([status, n]) =>
      el("span", { class: "badge badge-" + (STATUS_CLASS[status] || "neutral") }, n + " " + status));
    const advice = refused
      ? el("div", { class: "ag-import-advice ag-import-advice-bad" },
        el("strong", null, refused + " ligne(s) refusée(s) : rien n'a été écrit pour elles."),
        el("p", null, "Corrigez-les dans Excel (numéro de ligne ci-dessous), puis réimportez. Les lignes "
          + "déjà créées ont maintenant une clé : réexportez avant de réimporter tout le fichier, sinon elles "
          + "seraient créées une seconde fois."))
      : el("div", { class: "ag-import-advice ag-import-advice-ok" },
        el("strong", null, "Import complet : " + [["créée", "créée(s)"], ["mise à jour", "mise(s) à jour"],
          ["inchangée", "inchangée(s), rien à écrire"]].filter(([k]) => counts[k])
          .map(([k, l]) => counts[k] + " " + l).join(", ") + "."));
    const rows = report.map((r) => el("tr", { class: r.status === "refusée" ? "ag-row-refused" : null },
      el("td", { class: "nowrap muted" }, r.line ? String(r.line) : ""),
      el("td", { class: "nowrap" }, r.row),
      el("td", null, el("span", { class: "badge badge-" + (STATUS_CLASS[r.status] || "neutral") }, r.status)),
      el("td", null,
        (r.problems && r.problems.length ? r.problems : (r.reason ? [{ message: r.reason, fix: r.fix }] : []))
          .map((pb, i, all) => el("div", { class: "ag-import-problem" },
            el("div", { class: "ag-import-reason" }, (all.length > 1 ? (i + 1) + ". " : "") + pb.message),
            pb.fix ? el("div", { class: "ag-import-fix" }, "→ " + pb.fix) : null)),
        r.warning ? el("div", { class: "ag-import-warning" }, "⚠ " + r.warning) : null)));
    DA.modal("Résultat de l'import", el("div", { class: "ag-import-report" },
      el("div", { class: "ag-chips" }, chips),
      encodingNote ? el("p", { class: "ag-import-warning" }, "⚠ " + encodingNote) : null,
      result.note ? el("p", { class: "ag-import-warning" }, "⚠ " + result.note) : null,
      warnings && !refused ? el("p", { class: "ag-import-warning" }, "⚠ " + warnings
        + " ligne(s) appliquée(s) avec un avertissement (voir ci-dessous).") : null,
      advice,
      el("div", { class: "table-wrap ag-report" },
        DA.table(["Ligne Excel", "Ticket", "Résultat", "Détail et correctif"], rows))));
    const dialogs = document.querySelectorAll(".modal");
    dialogs[dialogs.length - 1].classList.add("modal-report");
  }

  /* Excel saves "CSV UTF-8" or, in French Windows, plain "CSV" in
     Windows-1252: read both instead of corrupting the accents. */
  async function readCsvFile(file) {
    const buffer = await file.arrayBuffer();
    try {
      return { text: new TextDecoder("utf-8", { fatal: true }).decode(buffer), note: "" };
    } catch (err) {
      return { text: new TextDecoder("windows-1252").decode(buffer),
        note: "Fichier lu en Windows-1252 (Excel « CSV » simple). Pour éviter tout risque sur les "
          + "accents, préférez Enregistrer sous → « CSV UTF-8 (délimité par des virgules) »." };
    }
  }

  function csvImportButton(ctx, kind, label, reload) {
    const input = el("input", { type: "file", accept: ".csv,text/csv", class: "ag-hidden-frame" });
    const button = el("button", { type: "button", class: "btn btn-small", onclick: () => input.click() }, label);
    input.addEventListener("change", async () => {
      const file = input.files[0];
      input.value = "";
      if (!file) return;
      if (!/\.csv$/i.test(file.name)) {
        toast("« " + file.name + " » n'est pas un .csv. Dans Excel : Fichier → Enregistrer sous → "
          + "CSV UTF-8 (délimité par des virgules).", "error");
        return;
      }
      button.disabled = true;
      try {
        const { text, note } = await readCsvFile(file);
        const result = await api.post(base(ctx) + "/import/" + kind, { csv: text });
        importReportModal(result, note);
        if (reload) reload();
      } catch (err) {
        DA.modal("Import impossible", el("div", { class: "ag-import-report" },
          el("div", { class: "ag-import-advice ag-import-advice-bad" }, el("strong", null, err.message))));
      } finally {
        button.disabled = false;
      }
    });
    return el("span", null, input, button);
  }

  function csvToolbar(ctx, reload) {
    return el("div", { class: "ag-csv-toolbar" },
      el("button", { type: "button", class: "btn btn-small",
        onclick: () => triggerDownload(downloadUrl(ctx, "tickets")) }, "Exporter les tickets (CSV)"),
      csvImportButton(ctx, "tickets", "Importer des tickets (CSV)", reload),
      el("button", { type: "button", class: "btn btn-small",
        onclick: () => triggerDownload(downloadUrl(ctx, "questions")) }, "Exporter les questions (CSV)"),
      csvImportButton(ctx, "questions", "Importer des réponses (CSV)", reload));
  }

  /* ---------- Shared filter bar (client side) ---------- */
  function filterBar(ctx, onChange) {
    const state = { text: "", assignee: "", type: "", label: "" };
    const text = el("input", { type: "search", placeholder: "Filtrer…", "aria-label": "Filtrer par texte" });
    const assignee = el("select", { "aria-label": "Assignee" },
      A.options([["none", "Unassigned"]].concat(ctx.meta.members.map((m) => [m.id, m.display_name])), "", "All Assignees"));
    const type = el("select", { "aria-label": "Type" },
      A.options(ctx.meta.types.map((t) => [t.id, t.name]), "", "All Types"));
    const label = el("select", { "aria-label": "Label" },
      A.options(ctx.meta.labels.map((l) => [l.name, l.name]), "", "All Labels"));
    const update = () => {
      Object.assign(state, { text: text.value.trim().toLowerCase(), assignee: assignee.value,
        type: type.value, label: label.value });
      onChange(state);
    };
    [text, assignee, type, label].forEach((c) => c.addEventListener("input", update));
    if (DA.myItems && DA.myItems()) {  // « Mes éléments » (D-B-033): start on my tickets
      assignee.value = String(DA.session.user.id);
      state.assignee = assignee.value || "";
    }
    return { bar: el("div", { class: "ag-filters" }, DA.mineBanner ? DA.mineBanner() : null, text, assignee, type, label), state };
  }

  function matches(issue, f) {
    if (f.text && !(issue.title.toLowerCase().includes(f.text) || issue.key.toLowerCase().includes(f.text))) return false;
    if (f.assignee === "none" && issue.assignee_id) return false;
    if (f.assignee && f.assignee !== "none" && String(issue.assignee_id) !== f.assignee) return false;
    if (f.type && String(issue.type_id) !== f.type) return false;
    if (f.label && !issue.labels.includes(f.label)) return false;
    return true;
  }

  /* ---------- Board ---------- */
  function card(ctx, issue) {
    const node = el("a", { class: "ag-card", href: "#/agile/" + ctx.key + "/issue/" + issue.number,
      draggable: A.canEditIssue(ctx, issue) ? "true" : null, "data-number": issue.number,
      title: A.canEditIssue(ctx, issue) ? null : "Seul le responsable du ticket le déplace" },
    el("span", { class: "ag-card-title" }, issue.title),
    issue.labels.length ? el("span", { class: "ag-chips" }, issue.labels.map(A.labelChip)) : null,
    el("span", { class: "ag-card-foot" },
      A.typeIcon(issue.icon_key, issue.type_name),
      el("span", { class: "ag-key" }, issue.key),
      A.priorityIcon(issue.priority),
      issue.story_points !== null ? el("span", { class: "ag-points", title: "Points" }, String(issue.story_points)) : null,
      A.avatar(issue.assignee_name)));
    node.addEventListener("dragstart", (ev) => {
      ev.dataTransfer.setData("text/plain", String(issue.number));
      ev.dataTransfer.effectAllowed = "move";
      node.classList.add("dragging");
    });
    node.addEventListener("dragend", () => node.classList.remove("dragging"));
    return node;
  }

  async function boardView(page, ctx) {
    const data = await api.get(base(ctx) + "/board");
    const sprint = data.sprint;
    const title = sprint ? sprint.name : "Board";
    page.append(A.pageHead(ctx, [el("span", null, title)]));
    page.append(el("p", { class: "muted ag-sub" }, sprint
      ? (sprint.goal || "Sprint actif") + (sprint.end_date ? " · fin prévue le " + sprint.end_date : "")
      : "Aucun sprint actif : tous les tickets ouverts, et ceux terminés depuis 14 jours."));

    if (!data.issues.length && !sprint) {  // D-B-134: a Space with no ticket yet
      page.append(DA.spaces.startHere("Le board de " + ctx.key + " est prêt",
        "Workflow standard (To Do → In Progress → In Review → Done), types Story, Task, Bug et Sub-task, Change Management "
        + "activé. Créez le premier ticket, ou importez une liste existante.",
        [A.canEdit(ctx) ? ["Créer le premier ticket", () => A.openCreate(ctx), true] : null,
          ["Importer des tickets (CSV)", A.href(ctx, "csv")], ["Planifier un Sprint", A.href(ctx, "backlog")]]));
    }
    const byNumber = new Map(data.issues.map((i) => [i.number, i]));
    const grid = el("div", { class: "ag-board" });
    const { bar, state } = filterBar(ctx, draw);
    page.append(bar, grid);

    function draw() {
      clear(grid);
      for (const status of columns(ctx)) {
        const items = data.issues.filter((i) => i.status_id === status.id && matches(i, state));
        const list = el("div", { class: "ag-column-body" }, items.map((i) => card(ctx, i)));
        const column = el("section", { class: "ag-column ag-col-" + status.category, "data-status": status.id },
          el("h2", { class: "ag-column-head" }, status.name, el("span", { class: "ag-count" }, String(items.length))),
          list);
        column.addEventListener("dragover", (ev) => { ev.preventDefault(); column.classList.add("drop"); });
        column.addEventListener("dragleave", () => column.classList.remove("drop"));
        column.addEventListener("drop", (ev) => { ev.preventDefault(); column.classList.remove("drop"); onDrop(ev, status); });
        grid.append(column);
      }
    }

    async function onDrop(ev, status) {
      const issue = byNumber.get(Number(ev.dataTransfer.getData("text/plain")));
      if (!issue || issue.status_id === status.id) return;
      const t = A.findTransition(ctx, issue, status.id);
      if (!t) {
        toast("Aucune transition de « " + issue.status_name + " » vers « " + status.name + " ».", "error");
        return;
      }
      try {
        await api.post(base(ctx) + "/issues/" + issue.number + "/transition", { transition_id: t.id });
        issue.status_id = status.id;
        issue.status_name = status.name;
        issue.status_category = status.category;
        draw();
      } catch (err) { toast(err.message, "error"); }
    }
    draw();
  }

  /* ---------- Backlog ---------- */
  function backlogRow(ctx, issue, siblings, reload, warning) {
    const editable = A.canEdit(ctx);
    const index = siblings.indexOf(issue);
    const move = el("select", { class: "ag-move", "aria-label": "Déplacer " + issue.key,
      disabled: !A.canEditIssue(ctx, issue) },
      A.options(ctx.meta.sprints.filter((s) => s.state !== "closed").map((s) => [s.id, s.name]),
        issue.sprint_id || "", "Backlog"));
    move.addEventListener("change", async () => {
      try { await api.patch(base(ctx) + "/issues/" + issue.number, { sprint_id: move.value || null }); reload(); }
      catch (err) { toast(err.message, "error"); }
    });
    async function rank(after) {
      try { await api.patch(base(ctx) + "/backlog/rank", { number: issue.number, after_number: after }); reload(); }
      catch (err) { toast(err.message, "error"); }
    }
    return el("li", { class: "ag-row ag-backlog-row" },
      warning ? el("span", { class: "ag-warning", title: warning, "aria-label": warning }, "⚠") : null,
      editable ? el("span", { class: "ag-rank" },
        el("button", { type: "button", class: "icon-btn", "aria-label": "Monter", disabled: index === 0,
          onclick: () => rank(index >= 2 ? siblings[index - 2].number : null) }, "↑"),
        el("button", { type: "button", class: "icon-btn", "aria-label": "Descendre", disabled: index === siblings.length - 1,
          onclick: () => rank(siblings[index + 1].number) }, "↓")) : null,
      A.typeIcon(issue.icon_key, issue.type_name), A.issueLink(ctx, issue),
      el("span", { class: "ag-row-title" }, issue.title),
      el("span", { class: "ag-chips" }, issue.labels.map(A.labelChip)),
      A.statusBadge(issue.status_name, issue.status_category),
      issue.story_points !== null ? el("span", { class: "ag-points" }, String(issue.story_points)) : null,
      A.avatar(issue.assignee_name), move);
  }

  function sprintDialog(ctx, sprint, reload) {
    const start = el("input", { type: "date", value: new Date().toISOString().slice(0, 10) });
    const end = el("input", { type: "date" });
    const goal = el("input", { type: "text", maxlength: 500, value: sprint.goal || "" });
    let close = null;
    close = modal("Démarrer " + sprint.name, el("form", { onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        await api.patch(base(ctx) + "/sprints/" + sprint.id, { goal: goal.value });
        await api.post(base(ctx) + "/sprints/" + sprint.id + "/start", { start_date: start.value, end_date: end.value || null });
        close();
        reload();
      } catch (err) { toast(err.message, "error"); }
    } }, field("Objectif", goal), el("div", { class: "form-row" }, field("Début", start), field("Fin", end)),
    el("div", { class: "form-actions" }, el("button", { type: "submit", class: "btn btn-primary" }, "Démarrer le sprint"))));
  }

  async function backlogView(page, ctx) {
    const [data, meta, deps] = await Promise.all([
      api.get(base(ctx) + "/issues?category=open&sort=rank"),
      api.get(base(ctx) + "/meta"),
      api.get(base(ctx) + "/dependencies"),
    ]);
    ctx.meta = meta;
    const reload = () => { clear(page); backlogView(page, ctx); };
    const issues = data.issues.slice().sort((a, b) => a.rank - b.rank);
    const editable = A.canEdit(ctx);
    page.append(A.pageHead(ctx, [el("span", { class: "ag-crumb-icon" }, A.roadmapIcon(), "Backlog")],
      editable ? el("button", { type: "button", class: "btn", onclick: async () => {
        try { await api.post(base(ctx) + "/sprints", {}); reload(); } catch (err) { toast(err.message, "error"); }
      } }, "Créer un sprint") : null));

    // H21 (option A, warning only): a ticket ranked before its blocker.
    const rankByNumber = new Map(issues.map((i) => [i.number, i.rank]));
    const warnings = new Map();
    for (const { blocker, blocked } of deps.blocks) {
      const rb = rankByNumber.get(blocker), rd = rankByNumber.get(blocked);
      if (rb === undefined || rd === undefined) continue;
      if (rd < rb) {
        warnings.set(blocked, "Ordonnancé avant son bloqueur (" + prefix(ctx) + "-" + blocker + ")");
      }
    }

    function section(title, subtitle, list, actions) {
      const points = list.reduce((sum, i) => sum + (i.story_points || 0), 0);
      return el("section", { class: "ag-sprint" },
        el("div", { class: "ag-sprint-head" },
          el("h2", null, title), el("span", { class: "muted" }, subtitle),
          el("span", { class: "muted" }, list.length + " ticket(s) · " + points + " pts"),
          el("span", { class: "ag-sprint-actions" }, actions || null)),
        list.length ? el("ul", { class: "ag-rows" },
          list.map((i) => backlogRow(ctx, i, list, reload, warnings.get(i.number))))
          : el("p", { class: "muted ag-empty-row" }, "Aucun ticket. Déplacez-en un ici avec la liste de droite."));
    }

    for (const sprint of meta.sprints.filter((s) => s.state !== "closed")) {
      const list = issues.filter((i) => i.sprint_id === sprint.id);
      const active = sprint.state === "active";
      const actions = !editable ? null : active
        ? el("button", { type: "button", class: "btn btn-small", onclick: async () => {
          if (!window.confirm("Clôturer " + sprint.name + " ? Les tickets non terminés retournent au backlog.")) return;
          try {
            const res = await api.post(base(ctx) + "/sprints/" + sprint.id + "/close");
            toast(sprint.name + " clôturé, " + res.returned_to_backlog + " ticket(s) renvoyé(s) au backlog.", "success");
            reload();
          } catch (err) { toast(err.message, "error"); }
        } }, "Clôturer")
        : [el("button", { type: "button", class: "btn btn-small", onclick: () => sprintDialog(ctx, sprint, reload) }, "Démarrer"),
          el("button", { type: "button", class: "btn btn-small btn-danger", onclick: async () => {
            try { await api.del(base(ctx) + "/sprints/" + sprint.id); reload(); } catch (err) { toast(err.message, "error"); }
          } }, "Supprimer")];
      page.append(section(sprint.name, active ? "Actif" + (sprint.end_date ? " jusqu'au " + sprint.end_date : "") : "À venir",
        list, actions));
    }
    page.append(section("Backlog", "", issues.filter((i) => !i.sprint_id)));
  }

  /* ---------- Ticket list ---------- */
  async function listView(page, ctx) {
    page.append(A.pageHead(ctx, [el("span", null, "Tickets")]));
    page.append(csvToolbar(ctx, () => load()));
    const q = el("input", { type: "search", placeholder: "Rechercher dans les titres et descriptions…",
      "aria-label": "Recherche plein texte" });
    const status = el("select", { "aria-label": "Status" }, A.options(
      [["cat:open", "Ouverts"], ["cat:done", "Terminés"]].concat(ctx.meta.statuses.map((s) => [s.id, s.name])),
      "cat:open", "All Statuses"));
    const type = el("select", { "aria-label": "Type" }, A.options(ctx.meta.types.map((t) => [t.id, t.name]), "", "All Types"));
    const assignee = el("select", { "aria-label": "Assignee" }, A.options(
      [["none", "Unassigned"]].concat(ctx.meta.members.map((m) => [m.id, m.display_name])), "", "All Assignees"));
    const label = el("select", { "aria-label": "Label" }, A.options(ctx.meta.labels.map((l) => [l.name, l.name]), "", "All Labels"));
    const sort = el("select", { "aria-label": "Tri" }, A.options([["", "Plus récents"], ["updated", "Modifiés récemment"],
      ["priority", "Priority"]], ""));
    const result = el("div");
    if (DA.myItems && DA.myItems()) assignee.value = String(DA.session.user.id);  // D-B-033
    page.append((DA.mineBanner && DA.mineBanner()) || "", el("div", { class: "ag-filters" }, q, status, type, assignee, label, sort), result);

    let timer = null;
    async function load() {
      const params = new URLSearchParams();
      if (q.value.trim()) params.set("q", q.value.trim());
      if (status.value.startsWith("cat:")) params.set("category", status.value.slice(4));
      else if (status.value) params.set("status", status.value);
      if (type.value) params.set("type", type.value);
      if (assignee.value) params.set("assignee", assignee.value);
      if (label.value) params.set("label", label.value);
      if (sort.value) params.set("sort", sort.value);
      try {
        const data = await api.get(base(ctx) + "/issues?" + params.toString());
        clear(result);
        result.append(DA.table(["Type", "Key", "Title", "Status", "Priority", "Assignee", "Labels", "Modifié"],
          data.issues.map((i) => el("tr", null,
            el("td", null, A.typeIcon(i.icon_key, i.type_name)),
            el("td", { class: "nowrap" }, A.issueLink(ctx, i)),
            el("td", null, el("a", { class: "ag-title-link", href: "#/agile/" + ctx.key + "/issue/" + i.number }, i.title)),
            el("td", null, A.statusBadge(i.status_name, i.status_category)),
            el("td", null, A.priorityIcon(i.priority), " ", A.PRIORITY[i.priority].label),
            el("td", null, i.assignee_name || el("span", { class: "muted" }, "—")),
            el("td", null, el("span", { class: "ag-chips" }, i.labels.map(A.labelChip))),
            el("td", { class: "nowrap muted" }, A.relativeDate(i.updated_at))))),
        el("p", { class: "muted ag-sub" }, data.issues.length + " ticket(s)" + (data.issues.length === 500 ? " (limite atteinte, affinez)" : "")));
      } catch (err) { toast(err.message, "error"); }
    }
    q.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(load, 250); });
    [status, type, assignee, label, sort].forEach((c) => c.addEventListener("change", load));
    load();
  }

  A.csvImportButton = csvImportButton;
  A.triggerDownload = (ctx, kind, query) => triggerDownload(downloadUrl(ctx, kind) + (query || ""));
  A.readCsvFile = readCsvFile;            // D-B-070: Goldmine preview import
  A.importReportModal = importReportModal;
  A.views.board = boardView;
  A.views.backlog = backlogView;
  A.views.issues = listView;
})();
