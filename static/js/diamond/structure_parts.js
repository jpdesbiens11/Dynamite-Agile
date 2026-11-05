/* Diamond · Structure fonctionnelle → « Pièces × fonctions » (0.60.20, D-O-031). The parts of the product tagged on the
   functions of the structure, as a matrix: one row per part, one column per function of the detail view. A cell is
   clicked to say « this part carries out this function ». Row and column counts show at once the integrated parts
   (several functions, in green) and the functions shared by several parts (to simplify, in orange); a function with no
   part is not designed yet. The architecture advice follows (fewer parts, fewer interfaces, lower cost). */
(function () {
  "use strict";

  const { el, field, toast } = DA;
  const D = DA.diamond;

  const code = (p) => "P-" + p.number;

  /* {function id: [parts]} -- for the boxes of the diagram: a sub-system also shows the parts of its tertiaries */
  function byFunction(data, view) {
    const out = new Map();
    const add = (fid, p) => { if (!out.has(fid)) out.set(fid, []); if (!out.get(fid).includes(p)) out.get(fid).push(p); };
    const detail = new Map(data.views.detail.map((f) => [f.id, f]));
    data.parts.forEach((p) => p.functions.forEach((fid) => {
      add(fid, p);
      const f = detail.get(fid);
      if (view === "general" && f && f.level === 3) add(f.parent_id, p);
    }));
    return out;
  }

  function stats(s) {
    const chip = (n, label, cls) => el("span", { class: "dm-pt-stat" + (cls ? " " + cls : "") }, el("strong", null, String(n)), " " + label);
    return el("div", { class: "dm-pt-stats", "aria-label": "Indicateurs" },
      chip(s.parts, s.parts > 1 ? "pièces" : "pièce"),
      chip(s.covered + " / " + s.functions, "fonctions réalisées"),
      chip(s.integrated, "pièce(s) intégrée(s) (2 fonctions ou plus)", s.integrated ? "dm-pt-good" : ""),
      chip(s.shared, "fonction(s) à plusieurs pièces", s.shared ? "dm-pt-warn" : ""),
      chip(String(s.ratio).replace(".", ","), "fonctions par pièce, en moyenne"));
  }

  function adder(state, run) {
    const name = el("input", { type: "text", maxlength: 80, placeholder: "ex. Boîtier de tête en aluminium", "aria-label": "Nom de la pièce" });
    const kind = el("select", { "aria-label": "Type de pièce" }, Object.entries(state.data.labels.part_kinds).map(([k, label]) =>
      el("option", { value: k }, label)));
    return el("form", { class: "ag-form dm-form dm-pt-add", "data-new": "0.60.20-part-add", onsubmit: (ev) => {
      ev.preventDefault();
      run("/parts", { name: name.value, kind: kind.value });
    } }, field("Nouvelle pièce", name), field("Type", kind),
    el("div", { class: "dm-actions" }, el("button", { type: "submit", class: "btn btn-small btn-primary" }, "Ajouter la pièce")));
  }

  function editRow(state, p, run) {
    const name = el("input", { type: "text", maxlength: 80, value: p.name, "aria-label": "Nom de " + code(p) });
    const kind = el("select", { "aria-label": "Type de " + code(p) }, Object.entries(state.data.labels.part_kinds).map(([k, label]) =>
      el("option", { value: k, selected: k === p.kind }, label)));
    const notes = el("input", { type: "text", maxlength: 1000, value: p.notes || "", placeholder: "Notes (matériau, procédé, fournisseur)",
      "aria-label": "Notes de " + code(p) });
    return el("form", { class: "ag-form dm-form dm-pt-edit", onsubmit: (ev) => {
      ev.preventDefault();
      state.editing = null;
      run("/parts/" + p.id, { name: name.value, kind: kind.value, notes: notes.value }, "patch");
    } }, el("div", { class: "dm-row" }, field("Nom", name), field("Type", kind)), field("Notes", notes),
    el("div", { class: "dm-actions" }, el("button", { type: "submit", class: "btn btn-small btn-primary" }, "Enregistrer"),
      el("button", { type: "button", class: "btn btn-small", onclick: () => { state.editing = null; state.redraw(); } }, "Annuler"),
      el("button", { type: "button", class: "btn btn-small btn-danger", onclick: () => {
        if (window.confirm("Effacer " + code(p) + " « " + p.name + " » et ses " + p.functions.length + " lien(s) ? L'action est journalisée.")) {
          state.editing = null;
          run("/parts/" + p.id + "/delete", {});
        }
      } }, "Effacer")));
  }

  function matrix(state, run, editable) {
    const data = state.data;
    const fns = data.views.detail.slice().sort((a, b) => a.number - b.number);  // the order of the tree
    const per = new Map(fns.map((f) => [f.id, data.parts.filter((p) => p.functions.includes(f.id)).length]));
    const head = el("tr", null, el("th", { scope: "col", class: "dm-pt-corner" }, "Pièce \\ fonction"),
      el("th", { scope: "col", class: "dm-pt-count" }, "Fonctions"),
      fns.map((f) => el("th", { scope: "col", class: "dm-pt-fn", "data-tip": "F" + f.number + " " + f.text },
        el("span", { class: "dm-code" }, "F" + f.number), el("span", { class: "dm-pt-fn-text" }, f.text))));
    const rows = data.parts.map((p) => {
      const n = p.functions.filter((fid) => per.has(fid)).length;
      const cells = fns.map((f) => {
        const on = p.functions.includes(f.id);
        const label = (on ? "Retirer : " : "Ajouter : ") + code(p) + " réalise F" + f.number;
        return el("td", { class: "dm-pt-cell" + (on ? " dm-pt-on" : "") }, editable
          ? el("button", { type: "button", class: "dm-pt-toggle", "aria-pressed": on ? "true" : "false", "aria-label": label, "data-tip": label,
            onclick: () => run("/parts/" + p.id + "/functions", { function_id: f.id, on: !on }, "put") }, on ? "●" : "")
          : (on ? "●" : ""));
      });
      const title = el("th", { scope: "row", class: "dm-pt-part" },
        el("span", { class: "dm-code" }, code(p)), " ", el("span", null, p.name), " ",
        el("span", { class: "badge badge-neutral dm-pt-kind" }, data.labels.part_kinds[p.kind] || p.kind),
        editable ? el("button", { type: "button", class: "link-btn dm-pt-edit-btn", "aria-label": "Modifier " + code(p),
          onclick: () => { state.editing = p.id; state.redraw(); } }, "Modifier") : null);
      const row = el("tr", { class: n === 0 ? "dm-pt-idle" : "" }, title,
        el("td", { class: "dm-pt-count" + (n >= 2 ? " dm-pt-good" : n === 0 ? " dm-pt-bad" : "") }, String(n)), cells);
      if (state.editing !== p.id) return [row];
      return [row, el("tr", { class: "dm-pt-editing" }, el("td", { colspan: fns.length + 2 }, editRow(state, p, run)))];
    }).flat();
    const foot = el("tr", { class: "dm-pt-foot" }, el("th", { scope: "row" }, "Pièces par fonction"), el("td", null, ""),
      fns.map((f) => { const n = per.get(f.id); return el("td", { class: "dm-pt-count" + (n >= 2 ? " dm-pt-warn" : n === 0 ? " dm-pt-bad" : "") }, String(n)); }));
    return el("div", { class: "dm-scroll dm-pt-scroll" }, el("table", { class: "data dm-pt-table", "data-new": "0.60.20-parts-matrix" },
      el("thead", null, head), el("tbody", null, rows), el("tfoot", null, foot)));
  }

  function advice(checks) {
    if (!checks.length) return null;
    return el("details", { class: "dm-advice", open: true }, el("summary", null, "Ce que dit l'architecture (" + checks.length + ")"),
      el("ul", null, checks.map((c) => el("li", null, c))));
  }

  /* the whole « Pièces × fonctions » view */
  function view(state, run, editable) {
    const data = state.data;
    const out = el("div", { class: "dm-pt", "data-new": "0.60.20-parts" },
      el("p", { class: "muted dm-pt-intro" }, "Quelles pièces réalisent quelles fonctions ? Une pièce qui assume plusieurs fonctions "
        + "réduit le nombre de pièces, d'interfaces et le coût ; une fonction qui demande plusieurs pièces est une piste de "
        + "simplification. Cliquez une case pour relier une pièce à une fonction."));
    if (!data.views.detail.length) {
      out.append(el("p", { class: "muted" }, "Aucune fonction dans la structure : construisez d'abord l'arbre fonctionnel."));
      return out;
    }
    if (data.parts.length) out.append(stats(data.part_stats), advice(data.part_checks), matrix(state, run, editable));
    else {
      out.append(el("div", { class: "dm-advice" }, el("p", null, "Aucune pièce encore. Nommez les pièces du concept retenu (ou les "
        + "sous-ensembles achetés), puis cochez les fonctions que chacune réalise."),
      editable ? el("button", { type: "button", class: "btn btn-small", onclick: () => run("/parts/example", {}) },
        "Charger les pièces de l'exemple (lampe de bureau)") : null));
    }
    if (editable) out.append(adder(state, run));
    return out;
  }

  /* the « Pièces » section of the panel of a function selected in the diagram */
  /* the « Pièces » section of the panel of a function selected in the diagram. 0.60.23: a sub-system of the general view
     also lists, and checks, the parts of its tertiary functions -- the same ones as the tags of its box -- with the
     function each one carries out; those are changed on the tertiary (detail view or matrix), not here. */
  function panelSection(state, fid, run, editable) {
    const data = state.data;
    const shown = byFunction(data, state.view).get(fid) || [];
    const direct = (p) => p.functions.includes(fid);
    const kids = data.views.detail.filter((f) => f.parent_id === fid && f.level === 3);
    const via = (p) => kids.filter((f) => p.functions.includes(f.id)).map((f) => "F" + f.number);
    const box = el("div", { class: "dm-reading dm-pt-panel", "data-new": "0.60.20-part-panel" },
      el("p", null, el("strong", null, "Pièces qui réalisent cette fonction (" + shown.length + ")")),
      shown.length ? el("p", { class: "dm-pt-chips" }, shown.map((p) => el("span", { class: "dm-pt-chip" + (direct(p) ? "" : " dm-pt-chip-via") },
        code(p) + " " + p.name + (direct(p) ? "" : " · par " + via(p).join(", ")))))
        : el("p", { class: "muted" }, "Aucune pièce."));
    if (!editable) return box;
    if (data.parts.length) {
      const checks = el("div", { class: "dm-pt-checks", "data-new": "0.60.23-part-via" }, data.parts.map((p) => {
        const inherited = !direct(p) && via(p).length > 0;
        const input = el("input", { type: "checkbox", checked: direct(p) || inherited, disabled: inherited });
        input.dataset.part = p.id;  // 0.60.26: several ticks, applied together (DA.choiceBatch)
        return el("label", { class: "dm-check" + (inherited ? " dm-pt-via" : ""),
          "data-tip": inherited ? "Réalise " + via(p).join(", ") + " (fonction tertiaire de ce sous-système) : modifiez-la dans la vue détaillée ou la matrice" : null },
        input, " " + code(p) + " " + p.name + (inherited ? " (par " + via(p).join(", ") + ")" : ""));
      }));
      box.append(checks);
      DA.choiceBatch(box, (list) => state.runMany(list.map((i) => ["/parts/" + i.dataset.part + "/functions",
        { function_id: fid, on: i.checked }, "put"])));
    }
    const name = el("input", { type: "text", maxlength: 80, placeholder: "Nouvelle pièce pour cette fonction", "aria-label": "Nouvelle pièce" });
    box.append(el("form", { class: "dm-row dm-pt-quick", onsubmit: (ev) => {
      ev.preventDefault();
      if (!name.value.trim()) { toast("Nommez la pièce.", "error"); return; }
      run("/parts", { name: name.value, kind: "designed", functions: [fid] });
    } }, name, el("button", { type: "submit", class: "btn btn-small" }, "Ajouter")));
    return box;
  }

  DA.diamond = Object.assign(DA.diamond || {}, { partsView: view, partsPanel: panelSection, partsByFunction: byFunction });
})();
