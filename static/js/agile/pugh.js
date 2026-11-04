/* Goldmine - « Pugh Matrix » (D-B-062): classic Pugh concept selection.
   Rows = Goldmine requirements picked from drop-downs (one requirement, a
   whole life-cycle phase or a category), columns = concepts. The datum
   (reference) column is S by definition; every other cell is +, S or -
   against it. Totals, net and rank are recomputed by the server after each
   change. Double-click a cell to write a note. URL: #/goldmine/KEY/pugh[/id]. */
(function () {
  "use strict";

  const { api, el, clear, field, toast, modal } = DA;
  const A = DA.agile;
  const SCORE_LABEL = { "+": "+ meilleur", S: "S pareil", "-": "− moins bon" };

  function base(ctx) { return "/api/agile/p/" + ctx.pid + "/pugh"; }
  const canWrite = (ctx, m) => A.canEdit(ctx) && m.status !== "decided";

  function wide() {
    const dialogs = document.querySelectorAll(".modal");
    if (dialogs.length) dialogs[dialogs.length - 1].classList.add("modal-wide");
  }

  /* ---------- List ---------- */
  async function listView(page, ctx) {
    const data = await api.get(base(ctx));
    page.append(A.pageHead(ctx, [el("span", null, "Matrices de Pugh")],
      A.canEdit(ctx) ? el("button", { type: "button", class: "btn btn-primary", onclick: () => openCreate(ctx) },
        "Nouvelle matrice") : null));
    page.append(el("p", { class: "muted pg-intro" }, "Sélection de concepts selon Pugh : chaque concept est comparé à une "
      + "référence (datum) sur chaque requirement Goldmine choisie comme critère — + meilleur, S pareil, − moins bon. "
      + "Le concept au meilleur total net sert de référence au tour suivant."));
    if (!data.matrices.length) {
      page.append(el("div", { class: "empty" }, el("p", null, "Aucune matrice pour ce Space.")));
      return;
    }
    page.append(DA.table(["Matrice", "Tour", "Concepts", "Critères", "Status", "Décision", "Modifiée"],
      data.matrices.map((m) => el("tr", null,
        el("td", null, el("a", { href: A.href(ctx, "pugh/" + m.id) }, m.title)),
        el("td", null, String(m.round)), el("td", null, String(m.n_concepts)), el("td", null, String(m.n_criteria)),
        el("td", null, el("span", { class: "badge pg-status-" + m.status }, m.status_label)),
        el("td", null, m.decision_name || el("span", { class: "muted" }, "—")),
        el("td", { class: "muted nowrap" }, DA.formatDate(m.updated_at) + (m.updated_by_name ? " · " + m.updated_by_name : ""))))));
  }

  function openCreate(ctx) {
    const title = el("input", { type: "text", maxlength: 200, placeholder: "ex. Fixation de l'élément chauffant" });
    const description = el("textarea", { rows: 2, maxlength: 4000, placeholder: "Question de conception à trancher" });
    const concepts = el("textarea", { rows: 4, placeholder: "Un concept par ligne (le premier est la référence)\nConcept A — vis\nConcept B — clips" });
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        const res = await api.post(base(ctx), { title: title.value, description: description.value,
          concepts: concepts.value.split("\n").map((x) => x.trim()).filter(Boolean) });
        close();
        location.hash = A.href(ctx, "pugh/" + res.matrix.id);
      } catch (err) { error.textContent = err.message; }
    } }, field("Title", title), field("Description", description), field("Concepts", concepts), error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer la matrice")));
    close = modal("Nouvelle Pugh matrix", form);
    title.focus();
  }

  /* ---------- One matrix ---------- */
  async function matrixView(page, ctx) {
    const [data, gm] = await Promise.all([api.get(base(ctx) + "/" + ctx.arg), api.get("/api/agile/p/" + ctx.pid + "/goldmine")]);
    const state = { data, reqs: gm.requirements || [] };
    const holder = el("div");
    page.append(holder);
    draw(holder, ctx, state);
  }

  async function act(holder, ctx, state, method, path, body, done) {
    try {
      state.data = await api[method](base(ctx) + "/" + state.data.matrix.id + path, body);
      if (done) toast(done, "success");
    } catch (err) { toast(err.message, "error"); }
    draw(holder, ctx, state);
  }

  function draw(holder, ctx, state) {
    clear(holder);
    const { matrix: m, concepts, criteria, totals, labels } = state.data;
    const editable = canWrite(ctx, m);
    const scores = new Map(state.data.scores.map((s) => [s.criterion_id + ":" + s.concept_id, s]));
    const run = (method, path, body, done) => act(holder, ctx, state, method, path, body, done);

    const actions = [
      el("a", { class: "btn", href: base(ctx) + "/" + m.id + "/export.xlsx", download: "" }, "Exporter (Excel)"),
      A.canEdit(ctx) && concepts.length ? el("button", { type: "button", class: "btn", onclick: () => openRound(ctx, state) }, "Nouveau tour") : null,
      A.canEdit(ctx) ? (m.status === "decided"
        ? el("button", { type: "button", class: "btn", onclick: () => run("patch", "", { status: "draft" }, "Matrice rouverte.") }, "Rouvrir")
        : el("button", { type: "button", class: "btn btn-primary", onclick: () => openDecide(holder, ctx, state) }, "Décider")) : null,
      A.isAdmin(ctx) ? el("button", { type: "button", class: "btn btn-danger", onclick: async () => {
        if (!window.confirm("Supprimer la matrice « " + m.title + " » ? L'action est journalisée.")) return;
        try { await api.del(base(ctx) + "/" + m.id); location.hash = A.href(ctx, "pugh"); } catch (err) { toast(err.message, "error"); }
      } }, "Supprimer") : null,
    ];
    holder.append(A.pageHead(ctx, [el("a", { href: A.href(ctx, "pugh") }, "Matrices de Pugh"), el("span", null, m.title)], actions));
    holder.append(el("div", { class: "pg-meta" },
      el("span", { class: "badge" }, "Tour " + m.round), el("span", { class: "badge pg-status-" + m.status }, m.status_label),
      el("span", { class: "muted" }, "Modifiée " + DA.formatDate(m.updated_at) + (m.updated_by_name ? " par " + m.updated_by_name : "")),
      editable ? el("button", { type: "button", class: "link-btn", onclick: () => openEdit(holder, ctx, state) }, "Renommer / décrire") : null));
    if (m.description) holder.append(el("p", { class: "pg-description" }, m.description));
    if (m.status === "decided") {
      const chosen = concepts.find((c) => c.id === m.decision_concept_id);
      holder.append(el("div", { class: "ag-import-advice ag-import-advice-ok" }, el("strong", null, "Décision : " + (chosen ? chosen.name : "?")),
        m.decision_note ? el("p", null, m.decision_note) : null));
    }
    if (editable) holder.append(toolbar(ctx, state, run));

    if (!concepts.length || !criteria.length) {
      holder.append(el("div", { class: "empty" }, el("p", null, !concepts.length
        ? "Ajoutez au moins deux concepts (le premier devient la référence)."
        : "Ajoutez des requirements comme critères : une à une, ou toute une life-cycle phase.")));
      if (!concepts.length || !criteria.length) return;
    }
    const best = Math.min(...concepts.filter((c) => c.id !== m.datum_id).map((c) => totals[c.id].rank));
    const head = el("tr", null, el("th", { scope: "col" }, "Requirement (critère)"), el("th", { scope: "col" }, "Phase"),
      concepts.map((c) => el("th", { scope: "col", class: "pg-concept" + (c.id === m.datum_id ? " pg-datum" : "") },
        el("span", { class: "pg-concept-name", title: c.description || "" }, c.name),
        c.id === m.datum_id ? el("span", { class: "pg-datum-tag" }, "Référence") : null,
        editable ? el("button", { type: "button", class: "link-btn pg-concept-edit", "aria-label": "Modifier " + c.name,
          onclick: () => openConcept(holder, ctx, state, c) }, "modifier") : null)),
      editable ? el("th", { scope: "col" }, "") : null);
    const body = criteria.map((k) => el("tr", { class: k.lifecycle ? "gm-row-lc gm-lc-" + k.lifecycle : null },
      el("th", { scope: "row", class: "pg-crit" },
        el("a", { class: "ag-key", href: "#/goldmine/" + ctx.key + "/issue/" + k.number }, k.key), " ",
        k.kind === "need" ? el("span", { class: "badge gm-need" }, "Need") : null,
        el("span", { title: k.statement || "" }, k.title),
        k.external_id ? el("span", { class: "muted pg-ext" }, " · " + k.external_id) : null),
      el("td", null, k.lifecycle ? el("span", { class: "gm-phase gm-lc-" + k.lifecycle }, labels.lifecycle[k.lifecycle] || k.lifecycle)
        : el("span", { class: "muted" }, "—")),
      concepts.map((c) => cell(ctx, state, run, k, c, scores.get(k.id + ":" + c.id), editable, c.id === m.datum_id)),
      editable ? el("td", null, el("button", { type: "button", class: "icon-btn", "aria-label": "Retirer " + k.key,
        title: "Retirer ce critère", onclick: () => run("del", "/criteria/" + k.id, undefined) }, "×")) : null));
    const foot = [["Σ +", "plus"], ["Σ S", "same"], ["Σ −", "minus"], ["Net (+ − −)", "net"], ["Rang", "rank"]].map(([label, k]) =>
      el("tr", { class: "pg-total pg-total-" + k }, el("th", { scope: "row", colspan: 2 }, label),
        concepts.map((c) => el("td", { class: "pg-num" + (k === "rank" && totals[c.id].rank === best && c.id !== m.datum_id ? " pg-best" : "") },
          String(totals[c.id][k]))), editable ? el("td") : null));
    holder.append(el("div", { class: "pg-wrap" }, el("table", { class: "data pg-matrix" },
      el("thead", null, head), el("tbody", null, body), el("tfoot", null, foot))));
    const unrated = concepts.filter((c) => c.id !== m.datum_id).reduce((n, c) => n + criteria.length - totals[c.id].rated, 0);
    holder.append(el("p", { class: "muted" }, unrated ? unrated + " case(s) encore à noter. " : "Toutes les cases sont notées. ",
      "Double-clic sur une case : ajouter une note (justification)."));
  }

  function cell(ctx, state, run, k, c, s, editable, isDatum) {
    if (isDatum) return el("td", { class: "pg-cell pg-S pg-datum-cell", title: "Référence : S par définition" }, "S");
    const value = s ? s.score : "";
    const td = el("td", { class: "pg-cell" + (value ? " pg-" + (value === "-" ? "minus" : value === "+" ? "plus" : "S") : ""),
      title: s && s.note ? s.note : "" });
    if (editable) {
      const sel = el("select", { "aria-label": k.key + " / " + c.name }, el("option", { value: "" }, "·"),
        Object.entries(SCORE_LABEL).map(([v, l]) => el("option", { value: v, selected: v === value }, l.split(" ")[0])));
      sel.addEventListener("change", () => run("put", "/score", { criterion_id: k.id, concept_id: c.id, score: sel.value, note: s ? s.note : "" }));
      td.append(sel);
      td.addEventListener("dblclick", () => openNote(ctx, state, run, k, c, s));
    } else {
      td.append(value === "-" ? "−" : value || "·");
    }
    if (s && s.note) td.append(el("span", { class: "pg-note-dot", "aria-hidden": "true" }, "•"));
    return td;
  }

  function toolbar(ctx, state, run) {
    const { concepts, criteria, matrix: m, labels } = state.data;
    const used = new Set(criteria.map((k) => k.number));
    const active = state.reqs.filter((r) => !["Rejected", "Obsolete"].includes(r.status_name) && !used.has(r.number));
    const byPhase = {};
    active.forEach((r) => { (byPhase[r.lifecycle || ""] = byPhase[r.lifecycle || ""] || []).push(r); });
    const req = el("select", { "aria-label": "Requirement à ajouter" }, el("option", { value: "" }, "— choisir un requirement Goldmine —"),
      Object.entries(byPhase).map(([phase, list]) => el("optgroup", { label: labels.lifecycle[phase] || "Phase non classée" },
        list.map((r) => el("option", { value: r.number }, (r.kind === "need" ? "[Need] " : "") + r.key + " · " + (r.external_id ? r.external_id + " · " : "") + r.title)))));
    const phase = el("select", { "aria-label": "Phase à ajouter" }, el("option", { value: "" }, "— toute une phase —"),
      Object.entries(labels.lifecycle).map(([v, l]) => el("option", { value: v }, l)));
    const category = el("select", { "aria-label": "Category à ajouter" }, el("option", { value: "" }, "— toute une category —"),
      Object.entries(labels.categories).map(([v, l]) => el("option", { value: v }, l)));
    const kind = el("select", { "aria-label": "Tous les needs ou toutes les requirements" }, el("option", { value: "" }, "— par nature —"),
      el("option", { value: "need" }, "tous les needs"), el("option", { value: "requirement" }, "toutes les requirements"));
    const addCrit = () => {
      const body = req.value ? { numbers: [Number(req.value)] } : kind.value ? { kind: kind.value } : phase.value ? { lifecycle: phase.value }
        : category.value ? { category: category.value } : null;
      if (!body) { toast("Choisissez un requirement, une phase ou une category.", "error"); return; }
      run("post", "/criteria", body, "Critère(s) ajouté(s).");
    };
    const concept = el("input", { type: "text", maxlength: 80, placeholder: "Nom du concept" });
    const datum = el("select", { "aria-label": "Référence (datum)" },
      concepts.map((c) => el("option", { value: c.id, selected: c.id === m.datum_id }, c.name)));
    datum.addEventListener("change", () => run("patch", "", { datum_id: Number(datum.value) }, "Nouvelle référence."));
    return el("div", { class: "pg-toolbar" },
      el("div", { class: "pg-tool" }, el("strong", null, "Critères"), req, kind, phase, category,
        el("button", { type: "button", class: "btn btn-small btn-primary", onclick: addCrit }, "Ajouter")),
      el("div", { class: "pg-tool" }, el("strong", null, "Concepts"), concept,
        el("button", { type: "button", class: "btn btn-small", onclick: () => {
          if (!concept.value.trim()) { concept.focus(); return; }
          run("post", "/concepts", { name: concept.value }, "Concept ajouté.");
        } }, "Ajouter"),
        concepts.length ? el("label", { class: "pg-datum-pick" }, "Référence (datum) ", datum) : null));
  }

  function openNote(ctx, state, run, k, c, s) {
    const note = el("textarea", { rows: 3, maxlength: 1000 });
    note.value = s ? s.note : "";
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: (ev) => {
      ev.preventDefault();
      close();
      run("put", "/score", { criterion_id: k.id, concept_id: c.id, score: s ? s.score : "", note: note.value });
    } }, el("p", { class: "muted" }, k.key + " · " + k.title + " — " + c.name), field("Note (pourquoi ce +, S ou −)", note),
    s ? null : el("p", { class: "muted" }, "Choisissez d'abord +, S ou − : la note accompagne une case notée."),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary", disabled: !s }, "Enregistrer")));
    close = modal("Note de la case", form);
    note.focus();
  }

  function openEdit(holder, ctx, state) {
    const m = state.data.matrix;
    const title = el("input", { type: "text", maxlength: 200, value: m.title });
    const description = el("textarea", { rows: 3, maxlength: 4000 });
    description.value = m.description;
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: (ev) => {
      ev.preventDefault();
      close();
      act(holder, ctx, state, "patch", "", { title: title.value, description: description.value }, "Matrice mise à jour.");
    } }, field("Title", title), field("Description", description),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
    close = modal("Matrice", form);
  }

  function openConcept(holder, ctx, state, c) {
    const name = el("input", { type: "text", maxlength: 80, value: c.name });
    const description = el("textarea", { rows: 3, maxlength: 1000 });
    description.value = c.description || "";
    let close = null;
    const path = "/concepts/" + c.id;
    const form = el("form", { class: "ag-form", onsubmit: (ev) => {
      ev.preventDefault();
      close();
      act(holder, ctx, state, "patch", path, { name: name.value, description: description.value }, "Concept mis à jour.");
    } }, field("Nom", name), field("Description", description),
    el("div", { class: "form-actions" },
      el("button", { type: "button", class: "btn btn-danger", onclick: () => {
        if (!window.confirm("Retirer le concept « " + c.name + " » et ses notes ?")) return;
        close();
        act(holder, ctx, state, "patch", path, { delete: true }, "Concept retiré.");
      } }, "Retirer"),
      el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
    close = modal("Concept", form);
  }

  function ranked(state) {
    const { concepts, totals } = state.data;
    return concepts.slice().sort((a, b) => totals[a.id].rank - totals[b.id].rank);
  }

  function openDecide(holder, ctx, state) {
    const list = ranked(state);
    const chosen = el("select", null, list.map((c) => el("option", { value: c.id },
      c.name + " — net " + state.data.totals[c.id].net + " (rang " + state.data.totals[c.id].rank + ")")));
    const note = el("textarea", { rows: 4, maxlength: 4000, placeholder: "Pourquoi ce concept : forces, risques acceptés, suites" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: (ev) => {
      ev.preventDefault();
      close();
      act(holder, ctx, state, "patch", "", { status: "decided", decision_concept_id: Number(chosen.value), decision_note: note.value },
        "Décision enregistrée.");
    } }, field("Concept retenu", chosen), field("Rationale", note),
    el("p", { class: "muted" }, "La matrice passe en lecture seule (journalisé) ; « Rouvrir » la rend de nouveau modifiable."),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Décider")));
    close = modal("Décider", form);
  }

  function openRound(ctx, state) {
    const list = ranked(state);
    const keep = list.map((c) => el("input", { type: "checkbox", value: c.id, checked: true }));
    const datum = el("select", null, list.map((c) => el("option", { value: c.id }, c.name)));
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      const kept = keep.filter((k) => k.checked).map((k) => Number(k.value));
      try {
        const res = await api.post(base(ctx) + "/" + state.data.matrix.id + "/round", { keep: kept, datum_id: Number(datum.value) });
        close();
        toast("Tour " + res.matrix.round + " créé.", "success");
        location.hash = A.href(ctx, "pugh/" + res.matrix.id);
      } catch (err) { toast(err.message, "error"); }
    } }, el("p", { class: "muted" }, "Classement du tour : décochez les concepts écartés. Mêmes critères, cases à renoter "
      + "contre la nouvelle référence (habituellement le meilleur concept)."),
    field("Concepts gardés", el("div", { class: "pg-keep" }, list.map((c, i) => el("label", { class: "check" }, keep[i],
      c.name + " (net " + state.data.totals[c.id].net + ")")))),
    field("Nouvelle référence (datum)", datum),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer le tour suivant")));
    close = modal("Nouveau tour", form);
    wide();
  }

  A.views.pugh = (page, ctx) => (ctx.arg ? matrixView(page, ctx) : listView(page, ctx));
})();
