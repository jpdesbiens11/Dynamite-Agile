/* Tools · Design - « Idéation » (D-B-066, D-B-073): divergent sessions --
   brainstorming, storytelling (this file), brainwriting 6-3-5 in rotating pairs
   (brainwriting.js) and mind map (mindmap.js). Idea cards with author, label,
   review attributes (impact, feasibility), « Rebondir » (build on an idea), stars
   ★ that bring the best ideas out of the log, then « Envoyer vers une matrice de
   Pugh ». The screen refreshes itself every few seconds (several people at once)
   without touching what is being typed. URL: #/tools/KEY/ideation[/id]. */
(function () {
  "use strict";

  const { api, el, clear, field, toast, modal } = DA;
  const A = DA.agile;
  const I = {};
  const base = (ctx) => "/api/tools/p/" + ctx.pid + "/ideation";
  const POLL_MS = 4000;
  I.base = base;

  async function listView(page, ctx, preset) {
    const data = await api.get(base(ctx));
    page.append(A.pageHead(ctx, [el("span", null, "Idéation")],
      A.canEdit(ctx) ? el("button", { type: "button", class: "btn btn-primary", onclick: () => openCreate(ctx, data.methods) },
        "Nouvelle séance") : null));
    page.append(el("p", { class: "muted tl-intro" }, "Phase divergente : beaucoup d'idées, sans juger. Brainstorming, brainwriting "
      + "6-3-5 (paires tournantes, en direct), mind map. Les meilleures idées (★) partent ensuite vers une "
      + "Pugh matrix. Pour raconter l'usage du produit scène par scène : Diamond → Storyline."));
    if (preset && A.canEdit(ctx)) openCreate(ctx, data.methods, preset);  // from a card of Tools · Design (#/tools/KEY/ideation/new-<method>)
    if (!data.sessions.length) { page.append(el("div", { class: "empty" }, el("p", null, "Aucune séance dans ce Space."))); return; }
    page.append(DA.table(["Séance", "Method", "Idées", "Status", "Modifiée"], data.sessions.map((s) => el("tr", null,
      el("td", null, el("a", { href: A.href(ctx, "ideation/" + s.id) }, s.title)), el("td", null, s.method_label),
      el("td", null, String(s.n_ideas)), el("td", null, s.status === "closed" ? "Close" : "Ouverte"),
      el("td", { class: "muted nowrap" }, DA.formatDate(s.updated_at) + (s.updated_by_name ? " · " + s.updated_by_name : ""))))));
  }

  function openCreate(ctx, methods, preset) {
    const title = el("input", { type: "text", maxlength: 200, placeholder: "ex. Atelier fixation des modules" });
    const method = el("select", null, Object.entries(methods).map(([k, l]) => el("option", { value: k, selected: k === preset }, l)));
    const prompt = el("textarea", { rows: 2, maxlength: 1000, placeholder: "Comment pourrions-nous… ?" });
    const minutes = el("input", { type: "number", min: 1, max: 60, value: 5 });
    const rounds = el("input", { type: "number", min: 1, max: 20, value: 6 });
    const perRound = el("input", { type: "number", min: 1, max: 10, value: 3 });
    const bwBox = el("div", { class: "form-row" }, field("Durée d'un tour (min)", minutes), field("Nombre de tours", rounds),
      field("Idées visées par tour", perRound));
    const sync = () => { bwBox.hidden = method.value !== "brainwriting"; prompt.placeholder = method.value === "mindmap" ? "Subject au centre de la carte" : "Comment pourrions-nous… ?"; };
    method.addEventListener("change", sync);
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        const res = await api.post(base(ctx), { title: title.value, method: method.value, prompt: prompt.value,
          round_minutes: Number(minutes.value), rounds: Number(rounds.value), ideas_per_round: Number(perRound.value) });
        close();
        location.hash = A.href(ctx, "ideation/" + res.session.id);
      } catch (err) { error.textContent = err.message; }
    } }, field("Titre", title), field("Method", method), field("Question de la séance", prompt), bwBox, error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer")));
    close = modal("Nouvelle séance d'idéation", form);
    sync();
    title.focus();
  }

  /* ---------- shared session plumbing ---------- */
  /* state: {data, ctx, redraw}; every call returns the whole session detail */
  I.act = async function (state, method, path, body) {
    try { state.data = await api[method](base(state.ctx) + "/" + state.data.session.id + path, body); }
    catch (err) { toast(err.message, "error"); }
    state.redraw();
  };

  /* Poll while the screen shows this session; skip when hidden or busy; redraw only on change */
  I.poll = function (state, holder) {
    const signature = (d) => JSON.stringify([d.ideas, d.links || null, d.bw || null, d.session.status, d.session.phase, d.session.title]);
    let last = signature(state.data);
    const timer = setInterval(async () => {
      if (!holder.isConnected) { clearInterval(timer); return; }
      if (document.hidden || state.busy) return;
      try {
        const data = await api.get(base(state.ctx) + "/" + state.data.session.id);
        const sig = signature(data);
        if (sig !== last) { last = sig; state.data = data; state.redraw(); }
      } catch (err) { /* offline for a moment: next tick */ }
    }, POLL_MS);
    state.remember = () => { last = signature(state.data); };
  };

  I.header = function (ctx, state) {
    const s = state.data.session;
    const open = s.status !== "closed";
    return [A.pageHead(ctx, [el("a", { href: A.href(ctx, "ideation") }, "Idéation"), el("span", null, s.title)], [
      el("a", { class: "btn", href: base(ctx) + "/" + s.id + "/export.csv", download: "" }, "Exporter (CSV)"),
      A.canEdit(ctx) ? el("button", { type: "button", class: "btn", onclick: () => I.act(state, "patch", "", { status: open ? "closed" : "open" }) },
        open ? "Clore la séance" : "Rouvrir") : null]),
    s.prompt ? el("p", { class: "tl-prompt" }, s.prompt) : null];
  };

  I.levelBadge = (label, value, levels) => (value ? el("span", { class: "badge tl-level tl-level-" + value }, label + " " + levels[value].toLowerCase()) : null);

  I.card = function (state, i, opts) {
    const { session: s, levels } = state.data;
    const open = s.status !== "closed";
    const canWrite = A.canEdit(state.ctx) && open;
    const mine = i.author_id === DA.session.user.id;
    const check = el("input", { type: "checkbox", "aria-label": "Choisir cette idée", checked: state.selected.has(i.id) });
    check.addEventListener("change", () => { if (check.checked) state.selected.add(i.id); else state.selected.delete(i.id); state.redraw(); });
    return el("article", { class: "tl-idea" + (i.stars ? " tl-starred" : "") + (opts && opts.partner ? " tl-partner" : ""), "data-id": i.id },
      el("div", { class: "tl-idea-top" }, check, i.tag ? el("span", { class: "badge" }, i.tag) : null,
        i.round ? el("span", { class: "badge" }, "Tour " + i.round) : null,
        I.levelBadge("Impact", i.impact, levels), I.levelBadge("Faisab.", i.feasibility, levels),
        el("span", { class: "muted tl-author" }, i.author_initials || "?")),
      i.parent_text ? el("div", { class: "tl-parent" }, "↳ rebond sur « " + i.parent_text.slice(0, 70) + (i.parent_text.length > 70 ? "…" : "") + " »") : null,
      el("p", { class: "tl-idea-text" }, i.text),
      el("div", { class: "tl-idea-actions" },
        open ? el("button", { type: "button", class: "btn btn-small tl-star" + (i.starred ? " on" : ""), "aria-pressed": i.starred ? "true" : "false",
          title: i.starred ? "Retirer mon étoile" : "Mettre une étoile", onclick: () => I.act(state, "post", "/ideas/" + i.id + "/star") },
        (i.starred ? "★ " : "☆ ") + i.stars) : el("span", { class: "badge" }, "★ " + i.stars),
        canWrite && (!opts || opts.rebound !== false) ? el("button", { type: "button", class: "btn btn-small", onclick: () => { state.parent = i; state.redraw(); state.focus && state.focus(); } }, "Rebondir") : null,
        canWrite ? el("button", { type: "button", class: "link-btn", onclick: () => I.sortIdea(state, i) }, "trier") : null,
        canWrite && mine ? el("button", { type: "button", class: "link-btn", onclick: () => I.editIdea(state, i) }, "modifier") : null));
  };

  /* Review and sorting: label and attributes, by any editor */
  I.sortIdea = function (state, i) {
    const { levels, tags, ideas } = state.data;
    const known = Array.from(new Set(tags.concat(ideas.map((x) => x.tag).filter(Boolean))));
    const tag = el("input", { type: "text", maxlength: 60, value: i.tag || "", list: "tl-sort-tags" });
    const pick = (value) => el("select", null, Object.entries(levels).map(([k, l]) => el("option", { value: k, selected: k === (value || "") }, l)));
    const impact = pick(i.impact);
    const feas = pick(i.feasibility);
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: (ev) => {
      ev.preventDefault();
      close();
      I.act(state, "patch", "/ideas/" + i.id, { tag: tag.value, impact: impact.value, feasibility: feas.value });
    } }, el("p", { class: "tl-idea-text" }, i.text), field("Étiquette (thème, groupe)", tag),
    el("datalist", { id: "tl-sort-tags" }, known.map((t) => el("option", { value: t }))),
    el("div", { class: "form-row" }, field("Impact", impact), field("Faisabilité", feas)),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
    close = modal("Trier l'idée", form);
    tag.focus();
  };

  I.editIdea = function (state, i) {
    const text = el("textarea", { rows: 3, maxlength: 1000 });
    text.value = i.text;
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: (ev) => { ev.preventDefault(); close(); I.act(state, "patch", "/ideas/" + i.id, { text: text.value }); } },
      field("Idée", text),
      el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn btn-danger", onclick: () => {
          if (!window.confirm("Retirer cette idée ? L'action est journalisée.")) return;
          close(); I.act(state, "patch", "/ideas/" + i.id, { delete: true });
        } }, "Retirer"),
        el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
        el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
    close = modal("Modifier l'idée", form);
  };

  /* Sort / filter / selection bar, shared by the list views */
  I.toolbar = function (state, groupLabel) {
    return el("div", { class: "tl-sort" },
      el("label", null, "Afficher ", el("select", { onchange: (ev) => { state.sort = ev.target.value; state.redraw(); } },
        [["group", groupLabel], ["stars", "par étoiles"], ["time", "par ordre d'arrivée"]]
          .map(([v, l]) => el("option", { value: v, selected: state.sort === v }, l)))),
      el("label", { class: "check" }, el("input", { type: "checkbox", checked: state.onlyStars,
        onchange: (ev) => { state.onlyStars = ev.target.checked; state.redraw(); } }), "★ seulement"),
      state.selected.size ? el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => I.toPugh(state) },
        "Envoyer " + state.selected.size + " idée(s) vers une Pugh matrix") : el("span", { class: "muted" },
        "Cochez les meilleures idées pour les évaluer dans une Pugh matrix."));
  };

  I.groups = function (state, ideas, groupOf) {
    let list = state.onlyStars ? ideas.filter((i) => i.stars) : ideas.slice();
    if (state.sort === "stars") list.sort((a, b) => b.stars - a.stars || a.id - b.id);
    const groups = new Map();
    if (state.sort === "group") list.forEach((i) => { const g = groupOf(i); if (!groups.has(g)) groups.set(g, []); groups.get(g).push(i); });
    else groups.set("", list);
    return groups;
  };

  /* Add form: kept between redraws so nothing typed is lost */
  I.addForm = function (state, extra) {
    const s = state.data.session;
    const text = el("textarea", { rows: 2, maxlength: 1000, placeholder: "Une idée par carte" });
    const tags = state.data.tags;
    const tag = tags.length
      ? el("select", { "aria-label": "Étiquette" }, el("option", { value: "" }, "— étiquette —"), tags.map((t) => el("option", { value: t }, t)))
      : el("input", { type: "text", maxlength: 60, placeholder: "Étiquette / thème", "aria-label": "Étiquette" });
    const rebound = el("div", { class: "tl-rebound" });
    const submit = () => {
      if (!text.value.trim()) { text.focus(); return; }
      const body = Object.assign({ text: text.value, tag: tag.value, parent_id: state.parent ? state.parent.id : null }, extra ? extra() : {});
      state.parent = null;
      text.value = "";
      I.act(state, "post", "/ideas", body).then(() => text.focus());
    };
    text.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) submit(); });
    const box = el("div", { class: "tl-add" }, rebound, text,
      el("div", { class: "tl-add-row" }, tag, el("button", { type: "button", class: "btn btn-primary", onclick: submit }, "Ajouter l'idée"),
        el("span", { class: "muted" }, "Ctrl + Entrée")));
    box.refresh = () => {
      clear(rebound);
      if (state.parent) rebound.append("Rebond sur : « " + state.parent.text.slice(0, 90) + " » ",
        el("button", { type: "button", class: "link-btn", onclick: () => { state.parent = null; box.refresh(); } }, "annuler"));
      box.hidden = s.status === "closed" || !A.canEdit(state.ctx);
    };
    state.focus = () => text.focus();
    return box;
  };

  I.toPugh = function (state) {
    const ctx = state.ctx;
    const byId = new Map(state.data.ideas.map((i) => [i.id, i]));
    const concepts = Array.from(state.selected).map((id) => byId.get(id)).filter(Boolean).map((i) => i.text.slice(0, 80));
    const title = el("input", { type: "text", maxlength: 200, value: state.data.session.title });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        const res = await api.post("/api/agile/p/" + ctx.pid + "/pugh", { title: title.value, description: "Concepts issus de "
          + "la séance « " + state.data.session.title + " » (" + state.data.session.method_label + ").", concepts });
        close();
        toast("Matrice créée : ajoutez les critères (needs, requirements).", "success");
        location.hash = A.href(ctx, "pugh/" + res.matrix.id);
      } catch (err) { toast(err.message, "error"); }
    } }, field("Titre de la matrice", title), el("p", { class: "muted" }, concepts.length + " concept(s) ; le premier devient la "
      + "référence (modifiable)."), el("ul", null, concepts.map((c) => el("li", null, c))),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer la matrice")));
    close = modal("Vers une Pugh matrix", form);
  };

  /* ---------- brainstorming, storytelling (and retired methods) ---------- */
  function plainView(page, ctx, data) {
    const state = { ctx, data, sort: "group", onlyStars: false, parent: null, selected: new Set() };
    const top = el("div");
    const add = I.addForm(state);
    const body = el("div");
    page.append(top, add, body);
    state.redraw = () => {
      clear(top);
      clear(body);
      const { session: s, ideas } = state.data;
      top.append(...I.header(ctx, state).filter(Boolean), el("div", { class: "pg-meta" }, el("span", { class: "badge" }, s.method_label),
        el("span", { class: "badge pg-status-" + (s.status === "closed" ? "decided" : "draft") }, s.status === "closed" ? "Close" : "Ouverte"),
        el("span", { class: "muted" }, ideas.length + " idée(s) · " + ideas.filter((i) => i.stars).length + " étoilée(s)")));
      add.refresh();
      body.append(I.toolbar(state, "par étiquette"));
      I.groups(state, ideas, (i) => i.tag || "Sans étiquette").forEach((items, name) => {
        body.append(name ? el("h3", { class: "tl-group" }, name + " (" + items.length + ")") : "",
          el("div", { class: "tl-ideas" }, items.map((i) => I.card(state, i))));
      });
      if (!ideas.length) body.append(el("div", { class: "empty" }, el("p", null, "Aucune idée pour l'instant.")));
    };
    state.redraw();
    I.poll(state, page);
  }

  async function sessionView(page, ctx) {
    const data = await api.get(base(ctx) + "/" + ctx.arg);
    const view = { brainwriting: DA.tools.brainwriting, mindmap: DA.tools.mindmap }[data.session.method] || plainView;
    view(page, ctx, data);
  }

  DA.tools = DA.tools || {};
  DA.tools.ideation = I;
  A.views.ideation = (page, ctx) => (ctx.arg && !ctx.arg.startsWith("new-") ? sessionView(page, ctx)
    : listView(page, ctx, ctx.arg ? ctx.arg.slice(4) : null));
})();
