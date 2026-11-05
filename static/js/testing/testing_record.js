/* « Testing » (D-B-079): one test record, #/testing/test/<ID> -- its fields, its procedure page (wiki TESTING),
   the Goldmine requirements that cite it in « Test Procedure » (Spaces you can see), its history; editable by
   the editors of TESTING. A catalogue test edited here no longer follows the code (it becomes the team's). */
(function () {
  "use strict";

  const { api, el, clear, field, toast } = DA;
  const T = (DA.testing = DA.testing || {});

  T.recordView = async function (main, testId) {
    const data = await api.get(T.api("/api/testing/tests/" + encodeURIComponent(testId)));
    const list = await api.get(T.api("/api/testing/tests"));
    const L = list.labels;
    const LI = list.lists;
    const nameOf = (kind, code) => (LI[kind].find((x) => x.code === code) || { label: code }).label;
    const t = data.test;
    const reload = () => { clear(main); T.recordView(main, testId); };
    const body = el("div");
    main.append(el("nav", { class: "tg-crumbs" }, el("a", { href: T.href("") }, "Testing · " + T.space), " › ",
      el("a", { href: T.href("subject/" + t.subject) }, L.subjects[t.subject] || t.subject), " › ", t.test_id),
    T.head(t.test_id + " · " + t.title, null, [
      t.procedure ? el("a", { class: "btn btn-small", href: T.pageHref(t.procedure) }, "Procedure " + t.procedure.title.split(" — ")[0]) : null,
      data.can_edit ? el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => edit() }, "Modifier") : null]),
    body);

    const row = (label, value) => el("div", { class: "gm-row" }, el("span", { class: "ag-field-label" }, label),
      el("span", null, value || el("span", { class: "muted" }, "—")));

    function show() {
      clear(body);
      body.append(el("div", { class: "tg-badges" }, T.catBadge(t.category, L), T.statusBadge(t.status),
        el("span", { class: "badge badge-neutral" }, t.origin === "catalog" ? (t.edited ? "Catalogue, modifié par l'équipe" : "Catalogue (suit le code)")
          : "Créé par l'équipe")),
      DA.review.box({ state: t.review, checked: t.review_checked, standard: t.standard, editable: data.can_edit, blocks: "Approved",
        url: T.api("/api/testing/tests/" + encodeURIComponent(t.test_id) + "/review"), done: reload }),
      el("div", { class: "ag-block tg-block" },
        el("div", { class: "gm-grid" }, row("Subject", L.subjects[t.subject]), row("Standard / référence", t.standard),
          row("Section", t.section), row("Level", t.level),
          row("Method", (t.method || "").split("").map((c) => c + " · " + (L.methods[c] || c)).join(" + "))),
        el("div", { class: "gm-grid" }, row("Test Location", t.location ? nameOf("location", t.location) : el("span", { class: "muted" }, "à planifier")),
          row("Functions", t.functions ? el("span", null, t.functions.split(", ").map((f, i) => (i ? " · " : "") + f + " "
            + nameOf("function", f)).join("")) : "")),
        row("Equipment", t.equipment ? el("ul", { class: "tg-eq" }, t.equipment.split(", ").map((c) => el("li", null,
          el("strong", null, c), " · " + nameOf("equipment", c)))) : ""),
        row("Source (traçabilité)", t.source),
        row("Procedure", t.procedure ? el("a", { href: T.pageHref(t.procedure) }, t.procedure.title) : ""),
        row("Objectif et déroulement", t.objective), row("Acceptance Criteria", t.acceptance),
        row("Test Means", t.means), row("Notes de l'équipe", t.notes)),
      el("h2", null, "Requirements qui citent ce test (" + data.requirements.length + ")"),
      data.requirements.length ? DA.table(["Requirement", "External ID", "Title", "Status"], data.requirements.map((r) => el("tr", null,
        el("td", { class: "nowrap" }, el("a", { class: "ag-key", href: T.reqHref(r.key) }, r.key)),
        el("td", { class: "nowrap" }, r.external_id || "—"), el("td", null, r.title), el("td", null, r.status))))
        : el("p", { class: "muted" }, "Aucune requirement de vos Spaces ne cite encore ce test (champ « Test Procedure » de la fiche requirement)."),
      el("h2", null, "History"),
      data.history.length ? el("ul", { class: "tg-history" }, data.history.map((h) => el("li", null,
        el("span", { class: "muted" }, DA.formatDate(h.at) + " · " + (h.who || "Système") + " — "), h.field,
        h.new_value ? " : " + (h.old_value ? h.old_value + " → " : "") + h.new_value : "")))
        : el("p", { class: "muted" }, t.origin === "catalog" ? "Test du catalogue, jamais modifié." : "—"));
    }

    function edit() {
      clear(body);
      const sel = (map, value) => el("select", null, Object.entries(map).map(([k, v]) => el("option", { value: k, selected: k === value }, v)));
      const text = (name, max) => el("input", { type: "text", maxlength: max, value: t[name] || "" });
      const area = (name, rows, max) => { const a = el("textarea", { rows, maxlength: max }); a.value = t[name] || ""; return a; };
      const f = {
        title: text("title", 200), subject: sel(L.subjects, t.subject), category: sel(L.categories, t.category),
        status: sel(Object.fromEntries(L.statuses.map((s) => [s, s])), t.status),
        standard: text("standard", 200), section: text("section", 200),
        level: sel(Object.fromEntries(L.levels.map((s) => [s, s])), t.level), method: text("method", 4),
        objective: area("objective", 4, 3000), acceptance: area("acceptance", 2, 2000), means: area("means", 2, 2000),
        notes: area("notes", 3, 3000),
        location: el("select", null, el("option", { value: "" }, "— à planifier —"), LI.location.filter((x) => x.active || x.code === t.location)
          .map((x) => el("option", { value: x.code, selected: x.code === t.location }, x.label))),
      };
      const eq = DA.gt.chipPicker(LI.equipment, t.equipment, { placeholder: "+ Ajouter un équipement (liste centrale)…", label: "Ajouter un équipement", empty: "Aucun équipement" });
      const fn = DA.gt.chipPicker(LI.function, t.functions, { placeholder: "+ Ajouter une fonction…", label: "Ajouter une fonction", empty: "Aucune fonction" });
      const error = el("p", { class: "form-error", role: "alert" });
      body.append(el("form", { class: "ag-form ag-block", onsubmit: async (ev) => {
        ev.preventDefault();
        try {
          const res = await api.patch(T.api("/api/testing/tests/" + encodeURIComponent(t.test_id)),
            Object.assign(Object.fromEntries(Object.entries(f).map(([k, i]) => [k, i.value])), { equipment: eq.value(), functions: fn.value() }));
          toast(res.changed.length ? "Test enregistré." : "Aucun changement.", "success");
          reload();
        } catch (err) { error.textContent = err.message; }
      } }, field("Title", f.title),
      el("div", { class: "form-row" }, field("Subject", f.subject), field("Category", f.category), field("Status", f.status,
        "« Obsolete » : ne peut plus être choisi pour une nouveau requirement")),
      el("div", { class: "form-row" }, field("Standard / référence", f.standard), field("Section", f.section)),
      el("div", { class: "form-row" }, field("Level", f.level), field("Method (IADT)", f.method), field("Test Location", f.location)),
      el("div", { class: "field" }, el("span", { class: "field-label" }, "Equipment (liste centrale)"), eq.node),
      el("div", { class: "field" }, el("span", { class: "field-label" }, "Functions"), fn.node),
      list.can_manage_lists ? null : el("p", { class: "field-hint" }, "Un équipement, un lieu ou une fonction manque ? Demandez-le à un Admin du Space DEMO (Testing → Listes)."),
      field("Objectif et déroulement", f.objective), field("Acceptance Criteria", f.acceptance),
      field("Test Means", f.means), field("Notes de l'équipe", f.notes), error,
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: show }, "Annuler"),
        el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer"))));
      f.title.focus();
    }
    show();
  };
})();
