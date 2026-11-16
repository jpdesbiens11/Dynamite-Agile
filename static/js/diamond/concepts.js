/* Diamond · « Briques technologiques » (0.60.105, D-O-117): #/diamond/KEY/concepts. The summary of the column « Concept / Brique
   technologique » of the tree: every brick that, combined with the others, makes the global concept. Grouped by the sub-system
   (secondary function) of its functions; for each brick, its nature (existing concept, or to define), its functions, its concept
   sheets as a morphological chart (the alternatives of each brick side by side; the selected one marked), and the Pugh matrices
   that judged it. #/diamond/KEY/concepts/CB-3 is one brick (concept_page.js). */
(function () {
  "use strict";

  const { api, el, clear, field, toast, modal } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  async function view(page, ctx) {
    if (ctx.arg) { await D.conceptPage(page, ctx); return; }
    const [data, sheets] = await Promise.all([api.get(D.base(ctx) + "/concepts"), api.get(D.base(ctx) + "/sheets")]);
    const state = { data, sheets: sheets.sheets };
    const holder = el("div", { class: "dm-page" });
    page.append(holder);
    draw(holder, ctx, state);
  }

  function draw(holder, ctx, state) {
    clear(holder);
    const { concepts, functions, labels } = state.data;
    const editable = A.canEdit(ctx);
    const reload = async () => {
      const [data, sheets] = await Promise.all([api.get(D.base(ctx) + "/concepts"), api.get(D.base(ctx) + "/sheets")]);
      state.data = data;
      state.sheets = sheets.sheets;
      D.later(() => draw(holder, ctx, state));
    };
    holder.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Briques technologiques")], [
      ...D.conceptAiButtons(ctx, editable, functions.length > 0, reload),
      editable ? el("button", { type: "button", class: "btn btn-small", onclick: () => openCreate(ctx, state, reload) }, "Nouvelle brique") : null,
      concepts.some((c) => c.kind === "to_define") && editable ? el("button", { type: "button", class: "btn btn-small btn-primary",
        onclick: () => D.openPughCreate(ctx, state.data, state.sheets) }, "Nouvelle matrice de Pugh") : null]));
    holder.append(el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.105-concepts" }, "Briques technologiques"),
      el("p", { class: "muted" }, "Les briques à combiner pour obtenir un concept global qui fonctionne. Chacune part d'un concept initial au nom qui "
        + "parle, l'idée qui rallie l'équipe, même si elle pivote ensuite. Une brique connue renvoie à un "
        + "concept existant ; une brique à définir s'invente avec des feuilles de concept (numériques, avec l'IA ou scannées), puis se "
        + "juge avec d'autres dans une matrice de Pugh, sur les besoins, les fonctions et les requirements.")));
    if (!concepts.length) { holder.append(empty(ctx, state, editable, reload, functions.length > 0)); return; }
    holder.append(counters(concepts), board(ctx, state), morpho(ctx, state));
  }

  function counters(concepts) {
    const n = (pred) => concepts.filter(pred).length;
    return el("div", { class: "dm-cb-counters" },
      el("span", { class: "badge badge-neutral" }, concepts.length + " briques"),
      el("span", { class: "badge badge-ok" }, n((c) => c.kind === "existing") + " concepts existants"),
      el("span", { class: "badge badge-warn" }, n((c) => c.kind === "to_define") + " à définir"),
      el("span", { class: "badge badge-info" }, n((c) => c.status === "selected") + " Selected"));
  }

  /* the bricks grouped by sub-system: the secondary function above their functions */
  function groups(state) {
    const fns = new Map(state.data.functions.map((f) => [f.id, f]));
    const subsystem = (f) => {
      let cur = f;
      while (cur && cur.level > 2 && fns.get(cur.parent_id)) cur = fns.get(cur.parent_id);
      return cur && cur.level === 2 ? cur : null;
    };
    const out = new Map();
    state.data.concepts.forEach((c) => {
      const first = c.function_ids.map((id) => fns.get(id)).find(Boolean);
      const sub = first ? subsystem(first) : null;
      const key = sub ? "F" + sub.number + " " + sub.text : "Sans fonction de l'arbre";
      if (!out.has(key)) out.set(key, []);
      out.get(key).push(c);
    });
    return out;
  }

  function board(ctx, state) {
    const fns = new Map(state.data.functions.map((f) => [f.id, f]));
    const L = state.data.labels;
    const wrap = el("div", { class: "dm-cb-board" });
    groups(state).forEach((list, title) => {
      wrap.append(el("section", { class: "dm-cb-group" }, el("h2", null, title),
        el("div", { class: "dm-cb-cards" }, list.map((c) => el("a", { class: "dm-cb-card dm-cb-" + c.kind + (c.status === "selected" ? " dm-cb-selected" : ""),
          href: A.href(ctx, "concepts/" + c.code) },
        el("div", { class: "dm-cb-top" }, el("span", { class: "dm-code" }, c.code),
          el("span", { class: "badge " + (c.kind === "existing" ? "badge-ok" : "badge-warn") }, L.kinds[c.kind]),
          el("span", { class: "badge badge-neutral" }, L.status[c.status]), c.source === "ai" ? el("span", { class: "badge badge-info" }, "IA") : null),
        c.initial_name ? el("strong", { class: "dm-concept-initial" }, "« " + c.initial_name + " »") : null,
        el(c.initial_name ? "span" : "strong", { class: "dm-cb-name" }, c.name),
        c.selected_sheet ? el("span", { class: "dm-concept-landed" }, "→ retenu : " + c.selected_sheet.code + " " + c.selected_sheet.title) : null,
        c.reference ? el("span", { class: "muted dm-cb-ref" }, "↳ " + c.reference) : null,
        el("span", { class: "dm-cb-fns" }, c.function_ids.map((id) => fns.get(id)).filter(Boolean).map((f) =>
          el("span", { class: "dm-chip", "data-tip": f.text }, "F" + f.number))),
        el("span", { class: "muted dm-cb-foot" }, c.sheets + " feuille" + (c.sheets > 1 ? "s" : "") + " · " + c.pughs.length
          + " matrice" + (c.pughs.length > 1 ? "s" : "") + " de Pugh"))))));
    });
    return wrap;
  }

  /* morphological chart: a row per brick to define, its sheets side by side -- the combinations the Pugh matrices judge */
  function morpho(ctx, state) {
    const rows = state.data.concepts.filter((c) => c.kind === "to_define" || c.sheets);
    if (!rows.length) return null;
    const max = Math.max(1, ...rows.map((c) => state.sheets.filter((s) => s.concept_id === c.id).length));
    return el("section", { class: "dm-cb-morpho", "data-new": "0.60.105-morpho" }, el("h2", null, "Tableau morphologique"),
      el("p", { class: "muted" }, "Une ligne par brique, ses feuilles de concept côte à côte. Un concept global prend une feuille par ligne ; "
        + "la feuille retenue par une matrice de Pugh est marquée."),
      el("div", { class: "pg-wrap" }, el("table", { class: "data dm-morpho" },
        el("thead", null, el("tr", null, el("th", { scope: "col" }, "Brique"), Array.from({ length: max }, (_, i) => el("th", { scope: "col" }, "Option " + (i + 1))))),
        el("tbody", null, rows.map((c) => {
          const list = state.sheets.filter((s) => s.concept_id === c.id);
          return el("tr", null, el("th", { scope: "row" }, el("a", { href: A.href(ctx, "concepts/" + c.code) }, c.code), " " + c.name),
            Array.from({ length: max }, (_, i) => {
              const s = list[i];
              return el("td", { class: s && s.status === "selected" ? "dm-morpho-on" : s && s.status === "dropped" ? "dm-morpho-off" : null },
                s ? [el("span", { class: "dm-code" }, s.code), " " + s.title] : el("span", { class: "muted" }, "—"));
            }));
        })))));
  }

  function openCreate(ctx, state, done) {
    const L = state.data.labels;
    const initial = el("input", { type: "text", maxlength: 80, placeholder: "ex. « Tête-radiateur »" });
    const name = el("input", { type: "text", maxlength: 120, placeholder: "ex. Gestion thermique de la tête" });
    const kind = el("select", null, Object.entries(L.kinds).map(([k, l]) => el("option", { value: k, selected: k === "to_define" }, l)));
    const reference = el("input", { type: "text", maxlength: 300, placeholder: "Pour un concept existant : technologie, composant, produit connu" });
    const free = state.data.functions.filter((f) => f.in_tree && f.level >= 2 && !state.data.concepts.some((c) => c.function_ids.includes(f.id)));
    const boxes = free.map((f) => el("input", { type: "checkbox", value: f.id }));
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        await api.post(D.base(ctx) + "/concepts", { name: name.value || initial.value, initial_name: initial.value, kind: kind.value, reference: reference.value,
          function_ids: boxes.filter((b) => b.checked).map((b) => Number(b.value)) });
        close();
        toast("Brique créée.", "success");
        done();
      } catch (err) { error.textContent = err.message; }
    } }, field("Concept initial : un nom qui parle", initial, "L'idée de départ qui rallie l'équipe ; elle pourra pivoter."),
    field("Brique technologique (ce qu'elle est, en termes techniques)", name), el("div", { class: "dm-row" }, field("Nature", kind), field("Référence", reference)),
    field("Fonctions qu'elle réalise (sans brique pour l'instant)", free.length ? el("div", { class: "dm-cb-pick" },
      free.map((f, i) => el("label", { class: "check" }, boxes[i], "F" + f.number + " " + f.text)))
      : el("p", { class: "muted" }, "Toutes les fonctions ont déjà leur brique.")), error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer")));
    close = modal("Nouvelle brique technologique", form);
    document.querySelectorAll(".modal").forEach((m) => m.classList.add("modal-wide"));
    name.focus();
  }

  function empty(ctx, state, editable, reload, hasTree) {
    return DA.spaces.startHere("Briques technologiques de " + ctx.meta.project.name,
      hasTree ? "Pour chaque fonction tertiaire de l'arbre, la brique qui la réalise. Demandez-les à un assistant IA (le prompt part de "
        + "votre arbre), ou créez-les une à une ; dans l'arbre, le panneau d'une fonction propose aussi sa brique."
        : "Les briques se rattachent aux fonctions de l'arbre fonctionnel : commencez par l'arbre.",
      editable ? (hasTree ? [["Créer une brique", () => openCreate(ctx, state, reload), true],
        ["Ouvrir l'arbre fonctionnel", () => { location.hash = A.href(ctx, "ftree"); }]]
        : [["Ouvrir l'arbre fonctionnel", () => { location.hash = A.href(ctx, "ftree"); }, true]]) : []);
  }

  A.views.concepts = view;
})();
