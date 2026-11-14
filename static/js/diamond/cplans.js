/* Diamond · « Plans de contrôle » (0.60.103, D-O-115), #/diamond/KEY/cplans/<plan>: the AIAG Control Plans of the Space, as
   on page 14 of the presentation. Several plans: the parts at reception, and the assembly steps of each line configuration;
   three phases (Prototype, Pré-lancement, Production) -- the same plan evolves, its phase and revision change. A row: No.,
   operation or part, machine / fixture, characteristic (class and specification read from its C-n), measurement technique,
   sample and frequency, control method, Reaction Plan. A CC without a Reaction Plan is flagged; a row whose C-n changed
   waits for a review (« à revoir »). */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;
  const COLS = [["equipment", "Machine · Jig"], ["technique", "Measurement Technique"], ["sample", "Sample"], ["frequency", "Frequency"],
    ["control_method", "Control Method"], ["reaction_plan", "Reaction Plan"]];

  async function view(page, ctx) {
    const base = D.base(ctx) + "/cplans";
    const holder = el("div", { class: "dm-page dm-cp-page" });
    page.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Plans de contrôle")]), holder);
    let data;
    try { data = await api.get(base); } catch (err) { holder.append(DA.spaces.startHere("Plans de contrôle réservés", err.message, [])); return; }
    const state = { ctx, base, holder, editable: A.canEdit(ctx), data, plan: Number(ctx.arg) || null, open: null };
    state.send = async (method, path, body, done) => {
      try {
        state.data = await api[method](base + path, body || {});
        if (done) toast(done, "success");
        draw(state);
        return state.data;
      } catch (err) { toast(err.message, "error"); return null; }
    };
    draw(state);
  }

  function draw(state) {
    const holder = state.holder, d = state.data, ctx = state.ctx;
    clear(holder);
    const plan = d.plans.find((p) => p.number === state.plan) || d.plans[0];
    holder.append(el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.103-cplans" }, "Plans de contrôle"),
      el("p", { class: "muted" }, "Qui mesure quoi, comment, et que faire si ça sort. Un plan pour les pièces à la réception et un par configuration de "
        + "ligne ; il passe de Prototype à Pré-lancement puis à Production sans être recopié.")));
    const pick = el("select", { "aria-label": "Plan de contrôle" }, d.plans.map((p) => el("option", { value: p.number, selected: plan && p.number === plan.number },
      p.code + " · " + p.title + (p.line ? " · " + p.line : "") + " · " + d.labels.phases[p.phase] + " · rév. " + p.revision)));
    pick.addEventListener("change", () => { location.hash = A.href(ctx, "cplans") + "/" + pick.value; });
    holder.append(el("div", { class: "dm-actions" }, d.plans.length ? pick : null,
      state.editable ? el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.103-cplan-new", onclick: () => planDialog(state, null) }, "Nouveau plan de contrôle") : null));
    if (d.checks.length) holder.append(el("details", { class: "dm-advice", open: true }, el("summary", null, "Conseils de la méthode (" + d.checks.length + ")"), el("ul", null, d.checks.map((c) => el("li", null, c)))));
    if (!plan) {
      holder.append(DA.spaces.startHere("Aucun plan de contrôle", "Un plan pour la réception des pièces, un par configuration de ligne (Diamond → Procédés).",
        state.editable ? [["Nouveau plan de contrôle", () => planDialog(state, null), true]] : []));
      return;
    }
    holder.append(el("div", { class: "dm-cp-head" }, el("h2", null, plan.code + " · " + plan.title),
      el("div", { class: "dm-actions", role: "group", "aria-label": "Phase" }, Object.entries(d.labels.phases).map(([k, label]) => el("button", { type: "button",
        class: "btn btn-small", "aria-pressed": String(plan.phase === k), disabled: !state.editable,
        onclick: () => state.send("patch", "/plans/" + plan.id, { phase: k }, plan.code + " : " + label + ".") }, label)),
      el("span", { class: "muted" }, el("span", null, d.labels.scopes[plan.scope]), plan.line ? " · " : null, plan.line ? el("span", null, plan.line) : null,
        " · ", el("span", null, "rév."), " " + plan.revision),
      state.editable ? el("button", { type: "button", class: "link-btn", onclick: () => planDialog(state, plan) }, "modifier") : null)));
    holder.append(table(state, plan));
  }

  function table(state, plan) {
    const asm = plan.scope === "assembly";
    const head = ["No.", asm ? "Operation" : "Part", "Characteristic", "Class", "Spec / Tolerance"].concat(COLS.map(([, l]) => l), [""]);
    const body = [];
    plan.items.forEach((r) => {
      body.push(el("tr", { class: "dm-fm-row" + (r.class_code ? " dm-fm-cls-" + r.class_code : "") + (r.review ? " dm-cp-review" : "") },
        el("td", { class: "dm-code nowrap" }, r.code, r.review ? el("div", { class: "dm-ch-miss" }, "à revoir") : null),
        el("td", null, asm ? (r.op ? "OP" + r.op + " " + r.op_name : "—") : (r.part || "—")),
        el("td", null, r.char_code ? el("span", { class: "dm-code" }, r.char_code + " ") : null, r.characteristic),
        el("td", null, r.class_code ? el("span", { class: "dm-cls dm-cls-" + r.class_code }, r.class_code === "CC" ? el("span", { class: "dm-cls-mark", "aria-hidden": "true" }, "▼") : null,
          r.class_symbol) : el("span", { class: "dm-cls dm-cls-none" }, r.nature === "process" ? "proc." : "—")),
        el("td", { class: "dm-ch-spec" }, r.spec || "—"),
        COLS.map(([k]) => el("td", { class: k === "reaction_plan" && r.class_code === "CC" && !r.reaction_plan ? "dm-ch-miss" : null },
          r[k] || (k === "reaction_plan" && r.class_code === "CC" ? "à écrire" : "—"))),
        el("td", { class: "nowrap" }, state.editable ? el("button", { type: "button", class: "link-btn", onclick: () => { state.open = state.open === r.id ? null : r.id; draw(state); } }, "modifier") : null)));
      if (state.open === r.id) body.push(el("tr", null, el("td", { colspan: head.length }, editor(state, plan, r))));
    });
    if (state.editable) body.push(el("tr", null, el("td", { colspan: head.length }, state.open === "new" ? editor(state, plan, null)
      : el("button", { type: "button", class: "btn btn-small", onclick: () => { state.open = "new"; draw(state); } }, "+ Ligne du plan"))));
    return el("div", { class: "dm-scroll dm-fm-scroll" }, el("table", { class: "data dm-fm dm-cp" }, el("thead", null, el("tr", null, head.map((h) => el("th", { scope: "col", class: "dm-fm-h" }, h)))),
      el("tbody", null, body)));
  }

  function editor(state, plan, r) {
    const d = state.data, line = d.lines.find((l) => l.id === plan.line_id);
    const opt = (pairs, value, label) => el("select", { "aria-label": label }, pairs.map(([v, t]) => el("option", { value: v, selected: String(value == null ? "" : value) === String(v) }, t)));
    const place = plan.scope === "assembly"
      ? opt([["", "— opération —"]].concat((line ? line.operations : []).map((o) => [o.id, "OP" + o.op + " · " + o.name])), r && r.operation_id, "Opération")
      : opt([["", "— pièce —"]].concat(d.parts.map((p) => [p.id, "P-" + p.number + " " + p.name])), r && r.part_id, "Pièce");
    const chr = opt([["", "— caractéristique de procédé (texte) —"]].concat(d.characteristics.map((c) => [c.id, c.code + (c.class_code ? " " + c.class_symbol : "") + " · " + c.label])),
      r && r.characteristic_id, "Caractéristique");
    const free = el("input", { type: "text", value: r ? r.char_label : "", placeholder: "ex. couple de la vis", "aria-label": "Caractéristique de procédé" });
    const inputs = Object.fromEntries(COLS.map(([k, l]) => [k, k === "reaction_plan" || k === "control_method" ? el("textarea", { rows: 2, "aria-label": l }, r ? r[k] : "")
      : el("input", { type: "text", value: r ? r[k] : "", "aria-label": l })]));
    const save = () => {
      const body = { characteristic_id: chr.value || null, char_label: free.value };
      body[plan.scope === "assembly" ? "operation_id" : "part_id"] = place.value || null;
      Object.entries(inputs).forEach(([k, i]) => { body[k] = i.value; });
      state.open = null;
      if (r) state.send("patch", "/items/" + r.id, body, r.code + " enregistrée."); else state.send("post", "/plans/" + plan.id + "/items", body, "Ligne ajoutée.");
    };
    return el("div", { class: "dm-pf-edit" }, el("div", { class: "dm-ch-grid" },
      el("fieldset", null, el("legend", null, "Quoi"), DA.field(plan.scope === "assembly" ? "Opération" : "Pièce", place), DA.field("Caractéristique C-n", chr),
        DA.field("ou caractéristique de procédé", free), DA.field("Machine · Jig", inputs.equipment)),
      el("fieldset", null, el("legend", null, "Comment"), DA.field("Measurement Technique", inputs.technique),
        el("div", { class: "dm-ch-row-f" }, DA.field("Sample", inputs.sample), DA.field("Frequency", inputs.frequency)), DA.field("Control Method", inputs.control_method)),
      el("fieldset", null, el("legend", null, "Si ça sort"), DA.field("Reaction Plan", inputs.reaction_plan, "Pour une CC : jusqu'au dernier bon contrôle, par le n° de série."))),
    el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn btn-primary", onclick: save }, "Enregistrer"),
      el("button", { type: "button", class: "btn", onclick: () => { state.open = null; draw(state); } }, "Fermer"),
      r ? el("button", { type: "button", class: "btn", onclick: () => { if (window.confirm("Retirer " + r.code + " du plan ?")) { state.open = null; state.send("patch", "/items/" + r.id, { delete: true }, r.code + " retirée."); } } }, "Retirer…") : null));
  }

  function planDialog(state, plan) {
    const d = state.data;
    const title = el("input", { type: "text", maxlength: 160, value: plan ? plan.title : "" });
    const scope = el("select", { disabled: !!plan }, Object.entries(d.labels.scopes).map(([k, l]) => el("option", { value: k, selected: plan ? plan.scope === k : k === "assembly" }, l)));
    const line = el("select", null, d.lines.map((l) => el("option", { value: l.id, selected: plan && plan.line_id === l.id }, l.code + " · " + l.name)));
    const phase = el("select", null, Object.entries(d.labels.phases).map(([k, l]) => el("option", { value: k, selected: plan ? plan.phase === k : k === "prototype" }, l)));
    const rev = el("input", { type: "text", maxlength: 12, value: plan ? plan.revision : "A", class: "dm-ch-short" });
    const err = el("p", { class: "dm-cls-err", role: "alert" });
    let close = () => {};
    const box = el("div", { class: "dm-cls-form" }, DA.field("Titre", title), DA.field("Portée", scope), DA.field("Configuration de ligne", line, "Pour les étapes d'assemblage"),
      DA.field("Phase", phase), DA.field("Révision", rev), err, el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
        const body = { title: title.value, phase: phase.value, revision: rev.value, line_id: scope.value === "assembly" ? line.value : null };
        try {
          state.data = plan ? await api.patch(state.base + "/plans/" + plan.id, body) : await api.post(state.base + "/plans", Object.assign(body, { scope: scope.value }));
          if (!plan) state.plan = state.data.plans[state.data.plans.length - 1].number;
          close();
          draw(state);
        } catch (e) { err.textContent = e.message; }
      } }, "Enregistrer"), el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler")));
    close = DA.modal(plan ? "Modifier " + plan.code : "Nouveau plan de contrôle", box);
    const m = box.closest(".modal");
    if (m) m.classList.add("dm-cls-modal");
  }

  A.views.cplans = view;
})();
