/* Diamond · Arbre fonctionnel, the bricks in the panel (0.60.105, D-O-117): « Concept / Brique » of the selected function (choose
   a brick, start a new one, leave it), and the panel of a selected brick (its name, existing concept or to define, reference,
   status, its functions). crun(path, body, method) writes to /api/diamond/p/<pid>/concepts… and redraws the tree. */
(function () {
  "use strict";

  const { el, field } = DA;
  const D = DA.diamond;

  function options(map, value) {
    return Object.entries(map).map(([k, label]) => el("option", { value: k, selected: k === value }, label));
  }

  /* the section of a function's panel */
  function brickPicker(state, f, crun, editable) {
    const cs = state.concepts.concepts;
    const mine = cs.find((c) => c.function_ids.includes(f.id));
    const wrap = el("div", { class: "dm-brick-pick", "data-new": "0.60.105-brick-pick" }, el("h3", null, "Concept / Brique technologique"));
    if (!editable) {
      wrap.append(el("p", null, mine ? mine.code + " " + mine.name : el("span", { class: "muted" }, "Aucune brique.")));
      return wrap;
    }
    const pick = el("select", { "aria-label": "Brique de " + "F" + f.number },
      el("option", { value: "" }, "— aucune brique —"), cs.map((c) => el("option", { value: c.id, selected: mine && c.id === mine.id },
        c.code + " " + c.name + (c.function_ids.length ? " (" + c.function_ids.length + " fonction" + (c.function_ids.length > 1 ? "s" : "") + ")" : ""))));
    pick.addEventListener("change", () => crun("/concepts/link", { function_id: f.id, concept_id: pick.value ? Number(pick.value) : null }));
    const name = el("input", { type: "text", maxlength: 80, placeholder: "Concept initial : un nom qui parle (ex. « Tête-radiateur »)", "aria-label": "Nouveau concept initial" });
    wrap.append(pick, el("p", { class: "muted dm-hint" }, "Plusieurs fonctions peuvent partager la même brique : choisissez-la dans la liste, "
      + "elle ne sera dessinée qu'une fois."),
    el("form", { class: "dm-actions", onsubmit: (ev) => {
      ev.preventDefault();
      if (!name.value.trim()) { name.focus(); return; }
      crun("/concepts", { name: name.value, initial_name: name.value, kind: "to_define", function_ids: [f.id] }, "post");
    } }, name, el("button", { type: "submit", class: "btn btn-small" }, "Nouveau concept")));
    return wrap;
  }

  /* the panel of a selected brick */
  function conceptPanel(state, c, crun, editable, ctx) {
    const L = state.concepts.labels;
    const fns = state.data.functions;
    const box = el("aside", { class: "dm-panel dm-panel-concept", "aria-label": "Brique " + c.code },
      el("div", { class: "dm-panel-head" }, el("span", { class: "dm-code dm-code-big" }, c.code),
        el("span", { class: "badge " + (c.kind === "existing" ? "badge-ok" : "badge-warn") }, L.kinds[c.kind])),
      el("p", { class: "muted dm-help" }, c.kind === "existing" ? "Une brique connue : on y renvoie, sans la réinventer."
        : "Une brique à inventer : feuilles de concept, puis une matrice de Pugh avec les autres briques du concept global."),
      c.source === "ai" ? el("p", { class: "dm-ai-note" }, "Brouillon IA : à relire par l'équipe.") : null,
      c.selected_sheet ? el("p", { class: "dm-reading" }, el("strong", null, "Idée de départ → retenu : "),
        (c.initial_name ? "« " + c.initial_name + " » → " : "") + c.selected_sheet.code + " " + c.selected_sheet.title) : null);
    const linked = c.function_ids.map((id) => fns.find((f) => f.id === id)).filter(Boolean);
    const list = el("ul", { class: "dm-brick-fns" }, linked.map((f) => el("li", null, el("span", { class: "dm-code" }, "F" + f.number), " " + f.text,
      editable ? el("button", { type: "button", class: "icon-btn", "aria-label": "Retirer F" + f.number + " de " + c.code,
        onclick: () => crun("/concepts/link", { function_id: f.id, concept_id: null }) }, "×") : null)));
    if (!editable) {
      box.append(c.initial_name ? el("p", { class: "dm-concept-initial" }, "« " + c.initial_name + " »") : null,
        el("p", null, el("strong", null, c.name)), c.pivot_note ? el("p", null, el("strong", null, "Pivot : "), c.pivot_note) : null, c.reference ? el("p", { class: "muted" }, c.reference) : null,
        c.description ? el("p", null, c.description) : null, el("h3", null, "Fonctions"), list);
    } else {
      const name = el("input", { type: "text", maxlength: 120, value: c.name });
      const initial = el("input", { type: "text", maxlength: 80, value: c.initial_name || "", placeholder: "ex. « Tête-radiateur »" });
      const pivot = el("textarea", { rows: 2, maxlength: 1000, placeholder: "Ce qui a changé depuis l'idée de départ, et pourquoi" }, c.pivot_note || "");
      const kind = el("select", null, options(L.kinds, c.kind));
      const status = el("select", null, options(L.status, c.status));
      const reference = el("input", { type: "text", maxlength: 300, value: c.reference, placeholder: "Concept existant, composant du marché…" });
      const description = el("textarea", { rows: 3, maxlength: 2000 }, c.description || "");
      box.append(el("form", { class: "ag-form dm-form", onsubmit: (ev) => {
        ev.preventDefault();
        crun("/concepts/" + c.id, { name: name.value, initial_name: initial.value, pivot_note: pivot.value, kind: kind.value, status: status.value, reference: reference.value,
          description: description.value }, "patch");
      } }, field("Concept initial : un nom qui parle", initial, "L'idée qui rallie l'équipe ; elle pourra pivoter après la divergence et la convergence."),
      field("Brique technologique (ce qu'elle est)", name), el("div", { class: "dm-row" }, field("Nature", kind), field("Status", status)),
      field("Référence", reference), field("Description", description),
      c.selected_sheet || c.pivot_note ? field("Pivot", pivot) : null,
      el("div", { class: "form-actions" }, el("button", { type: "submit", class: "btn btn-primary btn-small" }, "Enregistrer"))),
      el("h3", null, "Fonctions de la brique (" + linked.length + ")"), list,
      el("p", { class: "muted dm-hint" }, "Ajoutez une fonction depuis son propre panneau : « Concept / Brique technologique »."));
    }
    box.append(el("div", { class: "dm-actions" },
      el("a", { class: "btn btn-small btn-primary", href: DA.agile.href(ctx, "concepts/" + c.code) },
        "Feuilles de concept (" + c.sheets + ")"),
      editable ? el("button", { type: "button", class: "btn btn-small btn-danger", onclick: () => {
        if (window.confirm("Archiver " + c.code + " « " + c.name + " » ? Ses fonctions n'ont plus de brique ; ses feuilles et matrices restent. "
          + "Le numéro " + c.code + " ne sera jamais redonné.")) crun("/concepts/" + c.id + "/archive", {});
      } }, "Archiver") : null));
    return box;
  }

  D.brickPicker = brickPicker;
  D.conceptPanel = conceptPanel;
})();
