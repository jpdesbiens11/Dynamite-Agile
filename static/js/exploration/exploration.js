/* Exploration - top tab (D-B-019): per project, a multi-month plan of the
   ore extraction as a simple Gantt (phases, tasks, predecessors, weeks,
   owners, status). Administrators shape the plan (or import it from Excel);
   owners follow their tasks up. Not linked to Agile tickets. */
(function () {
  "use strict";

  const { api, el, clear, toast, modal, field } = DA;
  const EX = DA.exploration;
  const G = EX.gantt;
  const SCALE_KEY = "exploration.scale";
  let editMode = false;  // D-A-041: kept across reloads of the plan while the page is open

  const mark = () => el("img", { src: DA.mark("exploration"), alt: "", class: "ex-mark-img" });
  const base = (ctx) => "/api/exploration/p/" + ctx.pid;
  const fmt = (isoDate) => (isoDate ? new Date(isoDate + "T00:00:00").toLocaleDateString("fr-CA",
    { day: "2-digit", month: "short", year: "2-digit" }) : "—");
  function savedScale() {
    try { const v = localStorage.getItem(SCALE_KEY); return G.SCALES[v] ? v : "fit"; } catch (e) { return "fit"; }
  }
  function saveScale(v) { try { localStorage.setItem(SCALE_KEY, v); } catch (e) { /* private window */ } }

  /* ---------- Shell ---------- */
  function layout(main, ctx, active) {
    const page = el("section", { class: "ag-page ex-page" });
    const nav = [["plan", "Plan"], ["transfer", "Import / Export"]];
    main.append(el("div", { class: "ag-layout" },
      el("aside", { class: "ag-sidebar ag-shell-exploration" },
        el("div", { class: "ag-sidebar-mark" }, mark()),
        ctx ? el("select", { class: "ag-project-picker", "aria-label": "Space",
          onchange: (ev) => { location.hash = "#/exploration/" + ev.target.value + "/" + active; } },
        DA.session.projects.map((p) => el("option", { value: p.key, selected: p.key === ctx.key }, p.key + " · " + p.name))) : null,
        ctx ? el("nav", { class: "ag-nav", "aria-label": "Exploration" }, nav.map(([v, label]) =>
          el("a", { class: "ag-nav-item" + (active === v ? " active" : ""), href: "#/exploration/" + ctx.key + "/" + v,
            "aria-current": active === v ? "page" : null }, label))) : null,
        ctx ? DA.spaces.allLink("exploration") : DA.spaces.sidebar("exploration", (k) => "#/exploration/" + k + "/plan")),  // D-B-098
      page));
    return page;
  }

  function picker(main) {
    const page = layout(main, null);
    page.append(el("div", { class: "page-head" }, el("h1", null, "Exploration"),
      el("p", { class: "muted" }, "Plan du projet sur plusieurs mois (phases, tasks, Gantt). Choisissez un Space.")));
    if (!DA.session.projects.length) { page.append(el("div", { class: "empty" }, el("p", null, "Aucun Space accessible."))); return; }
    page.append(el("div", { class: "project-list" }, DA.session.projects.map((p) =>
      el("a", { class: "project ag-project-card", href: "#/exploration/" + p.key + "/plan" },
        el("div", { class: "project-top" }, el("span", { class: "key" }, p.key), DA.roleBadge(p.role)),
        el("h2", null, p.name), el("p", { class: "muted" }, p.description || "Aucune description.")))));
  }

  async function render(main, parts) {
    clear(main);
    main.classList.add("ag-main");
    const key = (parts[0] || "").toUpperCase();
    const project = DA.session.projects.find((p) => p.key === key);
    if (!project) {
      if (DA.spaces.enter("exploration", parts, (k) => "#/exploration/" + k + "/plan")) return;
      picker(main);
      return;
    }
    const ctx = { key, pid: project.id, project, view: parts[1] || "plan" };
    const page = layout(main, ctx, ctx.view === "transfer" ? "transfer" : "plan");
    try {
      ctx.data = await api.get(base(ctx) + "/plan");
      if (ctx.view === "transfer") EX.transferView(page, ctx, () => render(main, parts));
      else planView(page, ctx, () => render(main, parts));
    } catch (err) {
      page.append(el("div", { class: "empty" }, el("p", null, err.message)));
    }
  }

  /* ---------- Plan view ---------- */
  function canFollow(ctx, task) {
    return ctx.data.can_admin || (ctx.data.role === "editor" && task.owner_id === ctx.data.me);
  }

  function summary(tasks) {
    const count = (fn) => tasks.filter(fn).length;
    const end = tasks.reduce((m, t) => (t.end > m ? t.end : m), "");
    return el("div", { class: "ex-summary" },
      el("span", { class: "ex-chip" }, tasks.length + " task(s)"),
      el("span", { class: "ex-chip ex-chip-done" }, count((t) => t.status === "done") + " terminée(s)"),
      el("span", { class: "ex-chip ex-chip-doing" }, count((t) => t.status === "doing") + " en cours"),
      el("span", { class: "ex-chip ex-chip-late" }, count((t) => t.late) + " en retard"),
      el("span", { class: "ex-chip" }, "Fin prévue : " + fmt(end)));
  }

  function statusControl(ctx, task, reload) {
    if (!canFollow(ctx, task)) {
      return el("span", { class: "badge ex-status ex-status-" + task.status }, task.status_label);
    }
    const select = el("select", { class: "ex-status-select ex-status-" + task.status, "aria-label": "Status de " + task.code },
      ctx.data.statuses.map((s) => el("option", { value: s.key, selected: s.key === task.status }, s.label)));
    select.addEventListener("change", async () => {
      try { await api.patch(base(ctx) + "/tasks/" + task.id, { status: select.value }); reload(); }
      catch (err) { toast(err.message, "error"); reload(); }
    });
    return select;
  }

  function planView(page, ctx, reload) {
    const data = ctx.data;
    let scale = savedScale();
    let mine = !!(DA.myItems && DA.myItems());  // « Mes éléments » (D-B-033) checks « Mes tasks »
    const head = el("div", { class: "page-head ex-head" },
      el("div", null, el("h1", null, "Exploration — " + ctx.project.name),
        el("p", { class: "muted" }, "Plan du projet sur plusieurs mois : niveau abstrait, indépendant des tickets Agile.")));
    const start = el("input", { type: "date", value: data.start_date, disabled: !data.can_admin, "aria-label": "Plan Start" });
    start.addEventListener("change", async () => {
      try { await api.put(base(ctx) + "/plan", { start_date: start.value }); reload(); } catch (err) { toast(err.message, "error"); }
    });
    const scaleSel = el("select", { "aria-label": "Échelle du Gantt" },
      Object.entries(G.SCALES).map(([k, v]) => el("option", { value: k, selected: k === scale }, v.label)));
    scaleSel.addEventListener("change", () => { scale = scaleSel.value; saveScale(scale); draw(); });
    const mineBox = el("input", { type: "checkbox", checked: mine, disabled: editMode });
    mineBox.addEventListener("change", () => { mine = mineBox.checked; draw(); });
    /* D-A-041: edit mode (administrators) -- move tasks line by line (⠿ drag, ↑ ↓), into another phase, whole phases. */
    const editBtn = data.can_admin ? el("button", { type: "button", class: "btn" + (editMode ? " btn-primary" : ""),
      "aria-pressed": String(editMode), title: "Déplacer les tasks ligne par ligne et les redistribuer entre les phases",
      onclick: () => { editMode = !editMode; reload(); } }, editMode ? "✎ Mode édition : ON" : "✎ Mode édition : OFF") : null;
    const order = data.tasks.map((t) => ({ id: t.id, phase: t.phase }));
    async function send(next, message) {
      try { await api.put(base(ctx) + "/plan/order", { order: next }); if (message) toast(message, "success"); reload(); }
      catch (err) { toast(err.message, "error"); }
    }
    function moveTask(i, dir) {
      const next = order.map((x) => Object.assign({}, x));
      const j = i + dir;
      if (j < 0 || j >= next.length) return;
      if (next[j].phase !== next[i].phase) {  // at the edge of its phase: it joins the neighbouring phase
        next[i].phase = next[j].phase;
        send(next, "Déplacée dans la phase « " + (next[i].phase || "Sans phase") + " ».");
        return;
      }
      [next[i], next[j]] = [next[j], next[i]];
      send(next);
    }
    function segments() {
      const out = [];
      order.forEach((x, i) => { if (!out.length || out[out.length - 1].phase !== x.phase) out.push({ phase: x.phase, start: i, end: i });
        else out[out.length - 1].end = i; });
      return out;
    }
    function movePhase(start, dir) {
      const segs = segments();
      const k = segs.findIndex((s) => s.start === start);
      const other = segs[k + dir];
      if (!other) return;
      const [a, b] = dir < 0 ? [other, segs[k]] : [segs[k], other];
      send(order.slice(0, a.start).concat(order.slice(b.start, b.end + 1), order.slice(a.start, a.end + 1), order.slice(b.end + 1)));
    }
    let dragged = null;
    function dropAt(target, phase) {
      if (dragged === null) return;
      const next = order.map((x) => Object.assign({}, x));
      const from = next.findIndex((x) => x.id === dragged);
      const [item] = next.splice(from, 1);
      item.phase = phase;
      let at = target === null ? next.length : next.findIndex((x) => x.id === target);
      next.splice(at < 0 ? next.length : at, 0, item);
      dragged = null;
      send(next);
    }
    function dropZone(row, target, phase) {
      row.addEventListener("dragover", (ev) => { if (dragged !== null) { ev.preventDefault(); row.classList.add("ex-drop"); } });
      row.addEventListener("dragleave", () => row.classList.remove("ex-drop"));
      row.addEventListener("drop", (ev) => { ev.preventDefault(); row.classList.remove("ex-drop"); dropAt(target, phase); });
      return row;
    }
    const toolbar = el("div", { class: "ex-toolbar" },
      el("label", { class: "ex-inline" }, "Plan Start", start),
      el("label", { class: "ex-inline" }, "Échelle", scaleSel),
      el("label", { class: "check" }, mineBox, "Mes tasks"),
      el("span", { class: "ex-spacer" }), editBtn,
      el("a", { class: "btn", href: base(ctx) + "/export.xlsx", download: "" }, "Exporter Excel"),
      data.can_admin ? el("a", { class: "btn", href: "#/exploration/" + ctx.key + "/transfer" }, "Importer…") : null,
      data.can_admin ? el("button", { type: "button", class: "btn btn-primary", onclick: () => taskDialog(ctx, null, reload) },
        "+ Task") : null);
    const holder = el("div");
    page.append(head, toolbar, editMode ? el("p", { class: "ex-edit-help" }, "Mode édition : glissez une ligne par sa poignée ⠿ "
      + "(sur une task pour la placer avant elle, sur l'en-tête d'une phase pour la mettre en tête de cette phase), ou utilisez ↑ ↓. "
      + "Au bord de sa phase, ↑ / ↓ la fait passer dans la phase voisine. Les ↑ ↓ d'une phase déplacent toute la phase. "
      + "L'ordre est celui de l'affichage ; les dates suivent toujours durées et prédécesseurs.") : "",  // "" -- a null would print « null »
      summary(data.tasks), holder, legend());

    function draw() {
      clear(holder);
      const tasks = mine && !editMode ? data.tasks.filter((t) => t.owner_id === data.me) : data.tasks;
      const cols = editMode ? 9 : 8;
      if (!tasks.length) {
        holder.append(el("div", { class: "empty" }, el("p", null, mine ? "Aucune task ne vous est attribuée."
          : "Plan vide. Importez un fichier Excel ou ajoutez une task.")));
        return;
      }
      const r = G.range(data.tasks, data.start_date, data.today);
      const rows = [];
      let phase = null;
      tasks.forEach((t) => {
        if (t.phase !== phase) {
          phase = t.phase;
          const members = tasks.filter((x) => x.phase === phase);
          const start = data.tasks.indexOf(t);
          const segPhase = phase;
          const header = el("tr", { class: "ex-phase-row" },
            el("td", { colspan: cols }, el("strong", null, phase || "Sans phase"), el("span", { class: "muted" }, " · " + members.length),
              data.can_admin ? el("span", { class: "ex-phase-tools" },
                editMode ? [el("button", { type: "button", class: "link-btn", title: "Monter la phase", "aria-label": "Monter la phase "
                  + (phase || "Sans phase"), onclick: () => movePhase(start, -1) }, "↑"),
                el("button", { type: "button", class: "link-btn", title: "Descendre la phase", "aria-label": "Descendre la phase "
                  + (phase || "Sans phase"), onclick: () => movePhase(start, 1) }, "↓")] : null,
                el("button", { type: "button", class: "link-btn", title: "Ajouter une task à la fin de cette phase",
                  onclick: () => taskDialog(ctx, null, reload, { phase: segPhase }) }, "+ Task")) : null),
            el("td", { class: "ex-gantt-cell" }, G.phaseBar(members, r, scale)));
          rows.push(editMode ? dropZone(header, t.id, segPhase) : header);
        }
        const index = data.tasks.indexOf(t);
        const row = el("tr", { class: "ex-task-row" + (t.owner_id === data.me ? " ex-mine" : ""), draggable: editMode ? "true" : null },
          editMode ? el("td", { class: "ex-move" }, el("span", { class: "ex-grip", title: "Glisser pour déplacer", "aria-hidden": "true" }, "⠿"),
            el("button", { type: "button", class: "link-btn", "aria-label": "Monter " + t.code, disabled: index === 0,
              onclick: () => moveTask(index, -1) }, "↑"),
            el("button", { type: "button", class: "link-btn", "aria-label": "Descendre " + t.code, disabled: index === data.tasks.length - 1,
              onclick: () => moveTask(index, 1) }, "↓")) : null,
          el("td", { class: "ex-code" }, t.code),
          el("td", { class: "ex-title" }, el("button", { type: "button", class: "link-btn", onclick: () => taskDialog(ctx, t, reload),
            title: t.description || "Détails" }, t.title),
          t.predecessors.length ? el("span", { class: "ex-preds muted" }, "après " + t.predecessors.join(", ")) : null),
          el("td", null, t.owner_name || el("span", { class: "muted" }, "—")),
          el("td", { class: "ex-num" }, Number(t.duration_weeks) === 0 ? "milestone" : t.duration_weeks + " sem."),
          el("td", { class: "ex-date" }, fmt(t.start)),
          el("td", { class: "ex-date" + (t.late ? " ex-late-text" : "") }, fmt(t.end)),
          el("td", null, statusControl(ctx, t, reload)),
          el("td", { class: "ex-num" }, t.progress + " %"),
          el("td", { class: "ex-gantt-cell" }, G.bar(t, r, scale)));
        if (editMode) {
          row.addEventListener("dragstart", (ev) => { dragged = t.id; ev.dataTransfer.effectAllowed = "move";
            ev.dataTransfer.setData("text/plain", t.code); row.classList.add("ex-dragging"); });
          row.addEventListener("dragend", () => row.classList.remove("ex-dragging"));
          dropZone(row, t.id, t.phase);
        }
        rows.push(row);
      });
      holder.append(el("div", { class: "ex-grid-wrap" }, el("table", { class: "data ex-grid" },
        el("thead", null, el("tr", null, editMode ? el("th", { class: "ex-move" }, "Ordre") : null, ["ID", "Task", "Owner", "Duration", "Start", "Finish", "Status", "%"]
          .map((h) => el("th", null, h)), el("th", { class: "ex-gantt-cell" }, G.header(r, scale)))),
        el("tbody", null, rows))));
      if (scale === "fit" && !fitted) {  // second pass: spread the plan over the free width
        const wrap = holder.querySelector(".ex-grid-wrap");
        const cell = holder.querySelector("th.ex-gantt-cell");
        // At least ~half the width for the timeline; the table scrolls beyond that.
        const free = Math.max(wrap.clientWidth - cell.offsetLeft - 4, wrap.clientWidth * 0.5);
        const px = Math.max(0.8, Math.min(8, free / r.total));
        if (Math.abs(px - G.SCALES.fit.px) > 0.05) { G.SCALES.fit.px = px; fitted = true; draw(); fitted = false; }
      }
    }
    let fitted = false;
    draw();
    const onResize = () => { if (scale === "fit" && document.body.contains(holder)) draw(); };
    window.addEventListener("resize", onResize);
    window.addEventListener("hashchange", () => window.removeEventListener("resize", onResize), { once: true });
  }

  function legend() {
    const item = (cls, label) => el("span", { class: "ex-legend-item" }, el("span", { class: "ex-swatch " + cls }), label);
    return el("p", { class: "ex-legend muted" }, item("ex-planned", "Planifiée"), item("ex-done", "Terminée"),
      item("ex-late", "En retard"), item("ex-blocked", "Bloquée"), item("ex-milestone-sw", "Milestone"),
      item("ex-today-sw", "Aujourd'hui"));
  }

  /* ---------- Task dialog: full (admin), follow-up (owner) or read-only ---------- */
  function taskDialog(ctx, task, reload, preset) {
    const data = ctx.data;
    const admin = data.can_admin;
    const follow = task ? canFollow(ctx, task) : admin;
    const t = task || Object.assign({ code: "", phase: "", title: "", description: "", owner_id: null, duration_weeks: 1,
      start_date: "", predecessors: [], status: "todo", progress: 0, note: "" }, preset || {});
    const input = (name, value, attrs) => el("input", Object.assign({ name, value: value ?? "", disabled: !admin }, attrs || {}));
    const code = input("code", t.code, { maxlength: 20, placeholder: "auto (T1, T2…)" });
    const phase = input("phase", t.phase, { maxlength: 80, list: "ex-phases" });
    const title = input("title", t.title, { maxlength: 200, required: true });
    const description = el("textarea", { rows: 3, maxlength: 4000, disabled: !admin }, t.description);
    const owner = el("select", { disabled: !admin }, el("option", { value: "" }, "— non attribuée —"),
      data.members.map((m) => el("option", { value: m.id, selected: m.id === t.owner_id }, m.display_name)));
    const weeks = input("duration_weeks", t.duration_weeks, { type: "number", min: 0, max: 520, step: "0.5" });
    const imposed = input("start_date", t.start_date || "", { type: "date" });
    const preds = input("predecessors", (t.predecessors || []).join(", "), { placeholder: "ex. T1, T3" });
    const status = el("select", { disabled: !follow }, data.statuses.map((s) => el("option", { value: s.key, selected: s.key === t.status }, s.label)));
    const progress = el("input", { type: "number", min: 0, max: 100, step: 5, value: t.progress, disabled: !follow });
    const note = el("textarea", { rows: 2, maxlength: 500, disabled: !follow }, t.note);
    const error = el("p", { class: "form-error", role: "alert" });
    const phases = el("datalist", { id: "ex-phases" }, [...new Set(data.tasks.map((x) => x.phase).filter(Boolean))].map((p) => el("option", { value: p })));

    let close = null;
    async function submit(ev) {
      ev.preventDefault();
      error.textContent = "";
      const body = follow && !admin ? {} : { code: code.value, phase: phase.value, title: title.value, description: description.value,
        owner_id: owner.value ? Number(owner.value) : null, duration_weeks: weeks.value, start_date: imposed.value || null,
        predecessors: preds.value };
      if (follow) Object.assign(body, { status: status.value, progress: progress.value, note: note.value });
      try {
        if (task) await api.patch(base(ctx) + "/tasks/" + task.id, body);
        else await api.post(base(ctx) + "/tasks", body);
        close();
        toast(task ? "Task mise à jour." : "Task ajoutée.", "success");
        reload();
      } catch (err) { error.textContent = err.message; }
    }
    async function remove() {
      if (!window.confirm("Retirer " + task.code + " du plan ?")) return;
      try { await api.del(base(ctx) + "/tasks/" + task.id); close(); reload(); } catch (err) { error.textContent = err.message; }
    }
    const form = el("form", { class: "ex-form", onsubmit: submit },
      !admin ? el("p", { class: "muted" }, follow ? "Vous suivez cette task : status, avancement et note. La structure du plan "
        + "est gérée par un administrateur." : "Lecture seule : seul le responsable ou un administrateur modifie cette task.") : null,
      el("div", { class: "form-row" }, field("ID", code), field("Phase", phase)),
      field("Task", title), field("Description", description), phases,
      el("div", { class: "form-row" }, field("Owner", owner), field("Duration (weeks, 0 = milestone)", weeks)),
      el("div", { class: "form-row" }, field("Predecessors", preds, "Finish → Start, séparés par des virgules"),
        field("Start No Earlier Than", imposed, "Optionnel : pas avant cette date")),
      task ? el("p", { class: "muted" }, "Planifiée du " + fmt(task.start) + " au " + fmt(task.end)
        + (task.late ? " — en retard" : "") + ".") : null,
      el("div", { class: "form-row" }, field("Status", status), field("Progress (%)", progress)),
      field("Note de suivi", note),
      error,
      el("div", { class: "form-actions" },
        task && admin ? el("button", { type: "button", class: "btn btn-danger", onclick: remove }, "Retirer") : null,
        el("button", { type: "button", class: "btn", onclick: () => close() }, admin || follow ? "Annuler" : "Fermer"),
        admin || follow ? el("button", { type: "submit", class: "btn btn-primary" }, task ? "Enregistrer" : "Ajouter") : null));
    close = modal(task ? task.code + " — " + task.title : "Nouvelle task", form);
  }

  EX.base = base;
  DA.registerModule("exploration", render);
})();
