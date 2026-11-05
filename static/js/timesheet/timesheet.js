/* Timesheet - top tab (D-B-023): weekly time sheet of the signed-in person.
   Time ranges (day, project, task, hours, short description) are saved as
   they are typed; the week is submitted once every range has its
   description, then approved or returned by an administrator.
   Administrator screens (approval, Excel export, projects and organisms)
   live in manage.js. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const TS = (DA.timesheet = DA.timesheet || {});
  const mark = () => el("img", { src: DA.mark("timesheet"), alt: "", class: "tt-mark-img" });
  const hours = (h) => (Math.round(h * 100) / 100).toLocaleString("fr-CA") + " h";
  const iso = (d) => d.toISOString().slice(0, 10);
  const addDays = (s, n) => { const d = new Date(s + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return iso(d); };
  const longDate = (s) => new Date(s + "T12:00:00Z").toLocaleDateString("fr-CA", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
  TS.hours = hours;

  /* ---------- Shell ---------- */
  function layout(main, view, approver) {
    const admin = DA.session.user.is_admin;
    const nav = [["semaine", "Ma semaine"]].concat(approver ? [["approbation", "Approbation"]] : []);
    const adminItems = admin ? [["export", "Export et rapport Word"], ["projets", "Spaces et organismes"]] : [];  // D-A-039
    const page = el("section", { class: "ag-page tt-page" });
    main.append(el("div", { class: "ag-layout" },
      el("aside", { class: "ag-sidebar ag-shell-timesheet" },
        el("div", { class: "ag-sidebar-mark" }, mark()),
        el("nav", { class: "ag-nav", "aria-label": "Timesheet" }, nav.map(([v, label]) =>
          el("a", { class: "ag-nav-item" + (view === v ? " active" : ""), href: "#/timesheet/" + v,
            "aria-current": view === v ? "page" : null }, label)),
          DA.adminNav(adminItems, view, (v) => "#/timesheet/" + v))),
      page));
    return page;
  }

  async function render(main, parts) {
    clear(main);
    main.classList.add("ag-main");
    let info = {};
    try { info = await api.get("/api/timesheet/leave"); } catch (err) { /* keep the week view */ }
    const admin = DA.session.user.is_admin;
    const approver = admin || !!info.is_manager;  // D-B-031: a manager approves the weeks of his people
    let view = ["approbation", "export", "projets"].includes(parts[0]) ? parts[0] : "semaine";
    if ((view === "approbation" && !approver) || (["export", "projets"].includes(view) && !admin)) view = "semaine";
    const page = layout(main, view, approver);
    const reload = () => render(main, parts);
    try {
      if (view === "approbation") await TS.approvalView(page, reload);
      else if (view === "export") await TS.exportView(page);
      else if (view === "projets") await TS.projectsView(page, reload);
      else await weekView(page, parts[1] || "", (start) => { location.hash = "#/timesheet/semaine/" + start; });
    } catch (err) {
      page.append(el("div", { class: "empty" }, el("p", null, err.message)));
    }
  }

  /* ---------- Week view ---------- */
  async function weekView(page, startParam, goWeek) {
    const data = await api.get("/api/timesheet/week" + (startParam ? "?start=" + encodeURIComponent(startParam) : ""));
    const w = data.week;
    const editable = w.editable;
    const projects = {};
    data.projects.forEach((p) => { projects[p.id] = p; });
    const tasksOf = (pid) => {  // 0.60.41 (D-O-050): the Space's set, plus the leave codes every Space offers
      const own = (data.meta.task_sets[(projects[pid] || { task_set: "pdp" }).task_set] || { tasks: [] }).tasks;
      return own.concat((data.meta.leave || []).filter((t) => !own.some((o) => o.key === t.key)));
    };
    const refresh = () => { const holder = page; clear(holder); weekView(holder, w.start, goWeek); };

    const jump = el("input", { type: "date", value: w.start, "aria-label": "Aller à la semaine du" });
    jump.addEventListener("change", () => { if (jump.value) goWeek(jump.value); });
    page.append(
      el("div", { class: "page-head tt-head" },
        el("div", null, el("h1", null, "Ma feuille de temps"),
          el("p", { class: "muted" }, "Semaine du " + longDate(w.start) + " au " + longDate(w.end))),
        el("span", { class: "badge tt-status tt-status-" + w.status }, w.status_label)),
      el("div", { class: "tt-weeknav" },
        el("button", { type: "button", class: "btn btn-small", onclick: () => goWeek(addDays(w.start, -7)) }, "◀ Semaine précédente"),
        el("button", { type: "button", class: "btn btn-small", onclick: () => goWeek(data.today) }, "Cette semaine"),
        el("button", { type: "button", class: "btn btn-small", onclick: () => goWeek(addDays(w.start, 7)) }, "Semaine suivante ▶"),
        jump,
        el("span", { class: "tt-spacer" }),
        editable ? el("button", { type: "button", class: "btn btn-small tt-copy-week-btn", onclick: () => TS.copyWeekDialog(data, refresh),
          title: "Recopier les plages d'une semaine passée, jour pour jour" }, "⧉ Copier une semaine passée…") : null));
    if (w.status === "returned") {
      page.append(el("div", { class: "tt-banner tt-banner-warn" }, el("strong", null, "Renvoyée pour correction"),
        w.decided_by_name ? " par " + w.decided_by_name : "", w.note ? " : « " + w.note + " »" : "",
        el("div", { class: "muted" }, "Corrigez, puis soumettez de nouveau.")));
    } else if (w.status === "approved") {
      page.append(el("div", { class: "tt-banner tt-banner-ok" }, "Approuvée" + (w.decided_by_name ? " par " + w.decided_by_name : "")
        + ". La semaine est verrouillée."));
    } else if (w.status === "submitted") {
      page.append(el("div", { class: "tt-banner" }, "Soumise : en attente d'approbation. Vous pouvez la retirer pour la modifier."));
    }

    page.append(TS.leaveBanner(data.leave, false));
    page.append(el("div", { class: "tt-days" }, data.days.map((d, i) => el("div",
      { class: "tt-day" + (d === data.today ? " tt-today" : "") + (data.totals[d] > 0 ? " tt-day-filled" : "") },
      el("span", { class: "tt-day-label" }, data.day_labels[i]), el("strong", null, hours(data.totals[d])),
      editable && data.totals[d] > 0 ? el("button", { type: "button", class: "tt-day-copy", title: "Copier les plages de cette journée vers d'autres jours",
        onclick: () => TS.copyDaysDialog(data, data.entries.filter((e) => e.work_date === d).map((e) => e.id), d,
          "les " + data.entries.filter((e) => e.work_date === d).length + " plage(s) du " + data.day_labels[i], refresh) }, "⧉ Copier la journée") : null))));

    const missing = data.entries.filter((e) => !e.description.trim()).length;
    const rows = data.entries.map((e) => entryRow(e));
    page.append(el("div", { class: "table-wrap tt-table-wrap" }, el("table", { class: "data tt-table" },
      el("thead", null, el("tr", null, ["Jour", "Space", "Budget Line", "Heures", "Description (obligatoire pour soumettre)", ""]
        .map((h) => el("th", null, h)))),
      el("tbody", null, rows.length ? rows : el("tr", null, el("td", { colspan: 6, class: "muted" },
        editable ? "Aucune plage cette semaine. Cliquez « + Ajouter une plage »." : "Aucune plage cette semaine."))))));

    const submitBtn = el("button", { type: "button", class: "btn btn-primary", onclick: submit,
      "aria-describedby": "tt-submit-hint" }, "Soumettre la semaine");
    page.append(el("div", { class: "tt-footer" },
      editable && data.projects.length ? el("button", { type: "button", class: "btn", onclick: add }, "+ Ajouter une plage") : null,
      el("span", { class: "tt-total" }, "Total de la semaine : ", el("strong", null, hours(data.total))),
      el("span", { class: "tt-spacer" }),
      editable ? el("span", { id: "tt-submit-hint", class: missing ? "tt-hint-bad" : "muted" },
        missing ? missing + " description(s) manquante(s) — soumission bloquée" : "") : null,
      editable ? submitBtn : null,
      w.status === "submitted" ? el("button", { type: "button", class: "btn", onclick: recall }, "Retirer la soumission") : null));
    if (!data.projects.length) {
      page.append(el("p", { class: "muted" }, "Aucun Space ouvert aux feuilles de temps pour vous. Demandez à un administrateur."));
    }

    function entryRow(e) {
      if (!editable) {
        return el("tr", null, el("td", null, e.day_label), el("td", null, e.project_key),
          el("td", null, e.task_label), el("td", { class: "tt-num" }, hours(e.hours)), el("td", null, e.description || "—"), el("td"));
      }
      const day = el("select", { "aria-label": "Jour" }, data.days.map((d, i) =>
        el("option", { value: d, selected: d === e.work_date }, data.day_labels[i])));
      const project = el("select", { "aria-label": "Space" }, data.projects.map((p) =>
        el("option", { value: p.id, selected: p.id === e.project_id }, p.key + " · " + p.name)));
      if (!projects[e.project_id]) project.prepend(el("option", { value: e.project_id, selected: true }, e.project_key + " (fermé)"));
      const offered = tasksOf(e.project_id).filter((t) => t.active !== false || t.key === e.task_key);
      const task = el("select", { "aria-label": "Budget Line" }, offered
        .map((t) => el("option", { value: t.key, selected: t.key === e.task_key }, t.key + " · " + t.label + (t.active === false ? " (inactif)" : ""))));
      /* 0.60.20: a code that is no longer in the Funding Space of the Space (changed after the range was entered) is shown
         as it is, and flagged -- the list no longer shows the first code instead, which made it look saved */
      if (!offered.some((t) => t.key === e.task_key)) {
        task.prepend(el("option", { value: e.task_key, selected: true, disabled: true },
          e.task_key + " · hors du Funding Space — choisissez un code"));
        task.classList.add("tt-missing");
        task.setAttribute("data-new", "0.60.20-stale-code");
      }
      const h = el("input", { type: "number", min: 0.25, max: 24, step: 0.25, value: e.hours, class: "tt-hours", "aria-label": "Heures" });
      const desc = el("input", { type: "text", maxlength: 300, value: e.description || null, class: "tt-desc" + (e.description.trim() ? "" : " tt-missing"),
        placeholder: "Ex. revue du câblage du prototype 3", "aria-label": "Description" });
      const save = async (changes) => {
        try { await api.patch("/api/timesheet/entries/" + e.id, changes); refresh(); }
        catch (err) { toast(err.message, "error"); refresh(); }
      };
      day.addEventListener("change", () => save({ work_date: day.value }));
      project.addEventListener("change", () => save({ project_id: Number(project.value) }));
      task.addEventListener("change", () => save({ task_key: task.value }));
      h.addEventListener("change", () => save({ hours: Number(h.value) }));
      desc.addEventListener("input", () => desc.classList.toggle("tt-missing", !desc.value.trim()));
      desc.addEventListener("change", () => save({ description: desc.value }));
      const del = el("button", { type: "button", class: "icon-btn", "aria-label": "Supprimer la plage", title: "Supprimer",
        onclick: async () => {
          try { await api.del("/api/timesheet/entries/" + e.id); refresh(); } catch (err) { toast(err.message, "error"); }
        } }, "×");
      return el("tr", null, el("td", null, day), el("td", null, project), el("td", null, task),
        el("td", null, h), el("td", null, desc), el("td", { class: "tt-row-actions" },
          el("button", { type: "button", class: "icon-btn", "aria-label": "Copier la plage vers d'autres jours", title: "Copier vers d'autres jours",
            onclick: () => TS.copyDaysDialog(data, [e.id], e.work_date, "la plage « " + e.project_key + " · " + e.task_key + " · " + hours(e.hours) + " » du " + e.day_label, refresh) }, "⧉"),
          del));
    }

    async function add() {
      const last = data.entries[data.entries.length - 1];
      const day = data.days.includes(data.today) ? data.today : (last ? last.work_date : data.days[0]);
      const def = DA.spaces && DA.spaces.defaultKey ? DA.spaces.defaultKey() : "";  // 0.60.42 (D-O-051): the default Space first
      const mine = def ? data.projects.find((p) => p.key === def) : null;
      const pid = last && projects[last.project_id] ? last.project_id : (mine || data.projects[0]).id;
      try {
        await api.post("/api/timesheet/entries", { work_date: day, project_id: pid,
          task_key: last && last.project_id === pid && tasksOf(pid).some((t) => t.key === last.task_key && t.active !== false) ? last.task_key : undefined, hours: 1, description: "" });  // 0.60.20: never an old code
        refresh();
        setTimeout(() => { const all = page.querySelectorAll(".tt-desc"); if (all.length) all[all.length - 1].focus(); }, 150);
      } catch (err) { toast(err.message, "error"); }
    }

    async function submit() {
      if (missing) {
        toast("Soumission bloquée : " + missing + " plage(s) sans description (en rouge).", "error");
        const first = page.querySelector(".tt-missing");
        if (first) first.focus();
        return;
      }
      try { await api.post("/api/timesheet/week/submit", { start: w.start }); toast("Semaine soumise.", "success"); refresh(); }
      catch (err) { toast(err.message, "error"); }
    }

    async function recall() {
      try { await api.post("/api/timesheet/week/recall", { start: w.start }); refresh(); }
      catch (err) { toast(err.message, "error"); }
    }
  }

  DA.registerModule("timesheet", render);
})();
