/* Diamond · « Procédés » (0.60.103, D-O-113), #/diamond/KEY/process/<line>: the assembly line configurations of the
   Space -- the operations in order (OP10, OP20…) as on page 12 of the presentation, the equipment and fixtures of each, the
   control points with the characteristic C-n they protect (red CC, orange SC, green process check), the operation that
   closes the traceability of the CC. Shown to the members the « Admin du Space » chose (the panel « Accès »). */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  async function view(page, ctx) {
    const base = D.base(ctx) + "/process";
    const holder = el("div", { class: "dm-page dm-pr-page" });
    page.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Procédés")]), holder);
    let data;
    try { data = await api.get(base); } catch (err) {
      holder.append(DA.spaces.startHere("Procédés réservés", err.message, []));
      return;
    }
    const state = { ctx, base, holder, editable: A.canEdit(ctx), data, line: Number(ctx.arg) || null };
    state.send = async (method, path, body, done) => {
      try {
        state.data = await api[method](base + path, body || {});
        if (done) toast(done, "success");
        draw(holder, state);
        return state.data;
      } catch (err) { toast(err.message, "error"); return null; }
    };
    draw(holder, state);
  }

  function draw(holder, state) {
    clear(holder);
    const d = state.data, ctx = state.ctx;
    const line = d.lines.find((l) => l.number === state.line) || d.lines[0];
    holder.append(el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.103-process" }, "Procédés"),
      el("p", { class: "muted" }, "La ligne d'assemblage décrite pour le PFMEA et les plans de contrôle : les opérations dans l'ordre, l'équipement de "
        + "chacune, et les points de contrôle, chacun avec le numéro de la caractéristique qu'il protège. Un Space peut avoir plusieurs "
        + "configurations de ligne (prototypes, pré-série…).")));
    const pick = el("select", { "aria-label": "Configuration de ligne" }, d.lines.map((l) => el("option", { value: l.number, selected: line && l.number === line.number },
      l.code + " · " + l.name)));
    pick.addEventListener("change", () => { location.hash = A.href(ctx, "process") + "/" + pick.value; });
    holder.append(el("div", { class: "dm-actions" }, d.lines.length ? pick : null,
      state.editable ? el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.103-line-new", onclick: () => lineDialog(state, null) },
        "Nouvelle configuration de ligne") : null));
    if (d.checks.length) {
      holder.append(el("details", { class: "dm-advice", open: true }, el("summary", null, "Conseils de la méthode (" + d.checks.length + ")"),
        el("ul", null, d.checks.map((c) => el("li", null, c)))));
    }
    if (!line) {
      holder.append(DA.spaces.startHere("Aucune ligne d'assemblage", "Décrivez la ligne : ses opérations OP10, OP20…, l'équipement de chacune et les "
        + "points de contrôle des caractéristiques spéciales.", state.editable ? [["Nouvelle configuration de ligne", () => lineDialog(state, null), true]] : []));
    } else {
      holder.append(el("div", { class: "dm-pr-line-head" }, el("h2", null, line.code + " · " + line.name),
        line.description ? el("p", { class: "muted" }, line.description) : null,
        state.editable ? el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn btn-small", onclick: () => lineDialog(state, line) }, "Modifier la ligne"),
          el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => opDialog(state, line, null) }, "+ Opération")) : null),
      el("div", { class: "dm-pr-flow", "data-new": "0.60.103-process-flow" }, line.operations.map((o) => opCard(state, line, o))),
      el("p", { class: "dm-pr-legend" }, el("span", { class: "dm-pr-pt dm-pr-CC" }, "CC"), el("span", { class: "dm-pr-pt dm-pr-SC" }, "SC"),
        el("span", { class: "dm-pr-pt dm-pr-proc" }, "procédé"), " Chaque point de contrôle porte le numéro de la caractéristique qu'il protège."));
    }
    if (d.manager && d.access) holder.append(accessPanel(state));
  }

  function opCard(state, line, o) {
    const point = (p) => el("span", { class: "dm-pr-pt dm-pr-" + (p.class_code || "proc"), "data-tip": p.char_label ? p.char_label + " · " + p.spec : null },
      D.processPoint(p), state.editable ? el("button", { type: "button", class: "link-btn", "aria-label": "Retirer le point de contrôle",
        onclick: () => state.send("post", "/points/" + p.id + "/delete", {}, "Point de contrôle retiré.") }, "×") : null);
    return el("article", { class: "dm-pr-op" }, el("h3", null, el("span", { class: "dm-code" }, o.code), " " + o.name),
      o.equipment_list.length ? el("p", { class: "dm-pr-eq" }, o.equipment_list.join(", ")) : null,
      o.traceability ? el("p", { class: "dm-pr-trace" }, "Traçabilité : n° de série ↔ résultats des CC") : null,
      el("div", { class: "dm-pr-pts" }, o.points.map(point)),
      state.editable ? el("div", { class: "dm-actions" }, el("button", { type: "button", class: "link-btn", onclick: () => pointDialog(state, o) }, "+ contrôle"),
        el("button", { type: "button", class: "link-btn", onclick: () => opDialog(state, line, o) }, "modifier")) : null);
  }

  function form(title, fields, onSave) {
    const err = el("p", { class: "dm-cls-err", role: "alert" });
    let close = () => {};
    const box = el("div", { class: "dm-cls-form" }, fields, err, el("div", { class: "dm-actions" },
      el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
        try { await onSave(); close(); } catch (e) { err.textContent = e.message; }
      } }, "Enregistrer"), el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler")));
    close = DA.modal(title, box);
    const m = box.closest(".modal");
    if (m) m.classList.add("dm-cls-modal");
  }

  async function post(state, method, path, body, done) {
    state.data = await api[method](state.base + path, body);
    toast(done, "success");
    draw(state.holder, state);
  }

  function lineDialog(state, line) {
    const name = el("input", { type: "text", maxlength: 120, value: line ? line.name : "" });
    const desc = el("textarea", { rows: 3, maxlength: 1000 }, line ? line.description : "");
    form(line ? "Modifier " + line.code : "Nouvelle configuration de ligne", [DA.field("Nom", name, "ex. « Pré-série — atelier partenaire »"), DA.field("Description", desc)],
      async () => {
        if (line) await post(state, "patch", "/lines/" + line.id, { name: name.value, description: desc.value }, "Ligne enregistrée.");
        else {
          await post(state, "post", "/lines", { name: name.value, description: desc.value }, "Ligne créée.");
          state.line = state.data.lines[state.data.lines.length - 1].number;
          location.hash = A.href(state.ctx, "process") + "/" + state.line;
        }
      });
  }

  function opDialog(state, line, o) {
    const op = el("input", { type: "text", value: o ? "OP" + o.op : "", placeholder: "OP10", class: "dm-ch-short" });
    const name = el("input", { type: "text", maxlength: 120, value: o ? o.name : "" });
    const eq = el("textarea", { rows: 3, maxlength: 600, placeholder: "Une ligne par équipement ou gabarit" }, o ? o.equipment : "");
    const trace = el("input", { type: "checkbox", checked: !!(o && o.traceability) });
    const fields = [DA.field("Opération", op, o ? null : "Vide : la dizaine suivante"), DA.field("Nom", name), DA.field("Équipements et gabarits", eq),
      el("label", { class: "dm-check" }, trace, " Clôt la traçabilité des CC (n° de série ↔ résultats)")];
    if (o) {
      fields.push(el("button", { type: "button", class: "btn btn-small", onclick: () => {
        if (window.confirm("Retirer OP" + o.op + " et ses points de contrôle ? L'action est journalisée.")) state.send("post", "/ops/" + o.id + "/delete", {}, "Opération retirée.");
      } }, "Retirer l'opération…"));
    }
    form(o ? "Modifier OP" + o.op : "Nouvelle opération sur " + line.code, fields, async () => {
      const body = { op: op.value, name: name.value, equipment: eq.value, traceability: trace.checked };
      if (o) await post(state, "patch", "/ops/" + o.id, body, "Opération enregistrée.");
      else await post(state, "post", "/lines/" + line.id + "/ops", body, "Opération ajoutée.");
    });
  }

  function pointDialog(state, o) {
    const chars = state.data.characteristics;
    const pick = el("select", null, el("option", { value: "" }, "— contrôle de procédé, sans C-n —"),
      chars.map((c) => el("option", { value: c.id }, c.code + (c.class_code ? " " + c.class_symbol : "") + " · " + c.label)));
    const label = el("input", { type: "text", maxlength: 160, placeholder: "ex. étanchéité" });
    const method = el("input", { type: "text", maxlength: 160, placeholder: "ex. jauge go/no-go, poka-yoke + X̄-R, essai 100 %" });
    const freq = el("input", { type: "text", maxlength: 80, placeholder: "ex. chaque pièce, 1 par heure, par lot" });
    form("Point de contrôle à OP" + o.op, [DA.field("Caractéristique protégée", pick), DA.field("Ce qu'il vérifie (sans C-n)", label), DA.field("Méthode", method),
      DA.field("Fréquence", freq)], () => post(state, "post", "/ops/" + o.id + "/points",
      { characteristic_id: pick.value || null, label: label.value, method: method.value, frequency: freq.value }, "Point de contrôle ajouté."));
  }

  function accessPanel(state) {
    const boxes = state.data.access.map((m) => [m, el("input", { type: "checkbox", checked: m.granted, disabled: m.manager })]);
    return el("details", { class: "dm-pr-access", "data-new": "0.60.103-process-access" }, el("summary", null, "Accès (Admin du Space)"),
      el("p", { class: "muted" }, "Qui voit Procédés, PFMEA et Plans de contrôle dans ce Space : l'Admin du Space et les administrateurs toujours, "
        + "plus les membres cochés."),
      boxes.map(([m, box]) => el("label", { class: "dm-check" }, box, " " + m.name + (m.manager ? " (Admin du Space)" : ""))),
      el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => state.send("put", "/access",
        { user_ids: boxes.filter(([m, b]) => b.checked && !m.manager).map(([m]) => m.id) }, "Accès enregistrés.") }, "Enregistrer les accès"));
  }

  /* « C-14 SC · poka-yoke + X̄-R »: also used by the PFMEA and the control plans */
  D.processPoint = (p) => [[p.code, p.class_symbol].filter(Boolean).join(" ") || p.label, p.method, p.frequency].filter(Boolean).join(" · ");
  A.views.process = view;
})();
