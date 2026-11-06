/* Diamond · « Arbre fonctionnel » (0.60.11, D-O-023): #/diamond/KEY/ftree. The tree of the product's functions --
   « comment ? » to the right, « pourquoi ? » to the left up to the primary function, « quand ? » from top to bottom in
   the order of the first use (out of the box first, protection last) -- with the panel of the selected function, the
   functions « hors arbre » (estime, waiting), a list view and the method's advice. Numbers F1, F2… are kept for ever. */
(function () {
  "use strict";

  const { api, el, clear, field, toast, modal } = DA;
  const A = DA.agile;
  const D = DA.diamond;
  const KEYS = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right" };

  async function view(page, ctx) {
    const state = { data: await api.get(D.base(ctx) + "/functions"), selected: null, list: false };
    const holder = el("div", { class: "dm-page" });
    page.append(holder);
    const run = async (path, body, method) => {
      try {
        state.data = await api[method || "post"](D.base(ctx) + path, body || {});
        if (method === "post" && path === "/functions") {  // select the function just added
          const newest = state.data.functions.reduce((a, b) => (b.number > (a ? a.number : 0) ? b : a), null);
          if (newest) state.selected = newest.id;
        }
      } catch (err) { toast(err.message, "error"); }
      D.later(() => draw(holder, ctx, state, run));
    };
    draw(holder, ctx, state, run);
  }

  function draw(holder, ctx, state, run) {
    clear(holder);
    const items = state.data.functions;
    const editable = A.canEdit(ctx);
    if (!items.some((f) => f.id === state.selected)) state.selected = null;
    holder.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Arbre fonctionnel")],
      items.length ? [D.exportMenu(ctx, "tree"), el("button", { type: "button", class: "btn btn-small", "aria-pressed": state.list ? "true" : "false",
        onclick: () => { state.list = !state.list; D.later(() => draw(holder, ctx, state, run)); } }, state.list ? "Vue arbre" : "Vue liste")] : null));
    holder.append(el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.11-ftree" }, "Arbre fonctionnel"),
      el("p", { class: "muted" }, "Les fonctions du produit, de la fonction primaire (à gauche) à ses « comment » (à droite). De haut "
        + "en bas : l'ordre de la première utilisation, de la sortie de la boîte au service rendu ; la dernière branche protège.")));
    if (!items.length) { holder.append(empty(ctx, run, editable)); return; }
    holder.append(legend(), advice(state.data.checks));
    if (state.list) { holder.append(listView(state, holder, ctx, run)); return; }
    const select = (id) => { state.selected = state.selected === id ? null : id; D.later(() => draw(holder, ctx, state, run)); };
    const onDrop = (dragged, target) => run("/functions/" + dragged + "/move", { parent_id: target });
    const onKey = (ev, f) => {
      if (!ev.altKey || !KEYS[ev.key] || !editable) return;
      const move = D.moves(items, f)[KEYS[ev.key]];
      ev.preventDefault();
      state.selected = f.id;
      if (move) run("/functions/" + f.id + "/move", move);
    };
    const hasPrimary = items.some((f) => f.is_primary);
    const tree = hasPrimary ? D.drawTree({ items, selected: state.selected, editable, onSelect: select, onDrop, onKey })
      : el("div", { class: "empty" }, el("p", null, "Aucune fonction primaire. Choisissez-en une parmi les fonctions hors arbre "
        + "(« En faire la fonction primaire »), ou créez-la."), editable ? el("button", { type: "button", class: "btn btn-primary",
        onclick: () => ask("Fonction primaire", (text) => run("/functions", { text, primary: true }, "post")) }, "Créer la fonction primaire") : null);
    const chosen = items.find((f) => f.id === state.selected);
    holder.append(el("div", { class: "dm-work" + (chosen ? " dm-with-panel" : "") }, tree,
      chosen ? D.panel(state, chosen, run, editable) : el("aside", { class: "dm-panel dm-panel-idle" },
        el("p", { class: "muted" }, "Cliquez une fonction pour la lire (pourquoi ? comment ? quand ?), la modifier, lui ajouter un "
          + "« comment » ou la déplacer."))));
    holder.append(outside(state, holder, ctx, run, editable, select));
  }

  function legend() {
    return el("div", { class: "dm-legend", "aria-label": "Lecture de l'arbre" },
      el("span", { class: "dm-axis" }, "← Pourquoi ?"), el("span", { class: "dm-axis" }, "Comment ? →"), el("span", { class: "dm-axis" }, "Quand ? ↓"),
      el("span", { class: "dm-key dm-key-critical" }, "Chemin critique"), el("span", { class: "dm-key dm-key-feedback" }, "Rétroaction (contrôle)"),
      el("span", { class: "dm-key dm-key-tech" }, "Fonction technique"));
  }

  function advice(checks) {
    if (!checks.length) return el("p", { class: "dm-advice-ok" }, "L'arbre suit la méthode : primaire, secondaires, chemin critique.");
    return el("details", { class: "dm-advice", "data-new": "0.60.11-checks" }, el("summary", null, "Conseils de la méthode (" + checks.length + ")"),
      el("ul", null, checks.map((c) => el("li", null, c))));
  }

  function outside(state, holder, ctx, run, editable, select) {
    const items = state.data.functions.filter((f) => !f.in_tree);
    const zone = el("section", { class: "dm-outside", "aria-label": "Fonctions hors arbre", "data-new": "0.60.11-outside" },
      el("h2", null, "Hors arbre"), el("p", { class: "muted" }, "Fonctions d'estime, fonctions en attente ou retirées de l'arbre. "
        + "Glissez une boîte de l'arbre ici pour la retirer ; glissez une carte d'ici sur une boîte pour la placer."));
    const cards = el("div", { class: "dm-cards" }, items.length ? items.map((f) => card(f, state, select, editable, run))
      : el("p", { class: "muted" }, "Aucune pour l'instant."));
    zone.append(cards);
    if (editable) {
      zone.addEventListener("dragover", (ev) => { ev.preventDefault(); zone.classList.add("dm-drop"); });
      zone.addEventListener("dragleave", () => zone.classList.remove("dm-drop"));
      zone.addEventListener("drop", (ev) => {
        if (ev.defaultPrevented) return;
        ev.preventDefault();
        zone.classList.remove("dm-drop");
        const dragged = Number(ev.dataTransfer.getData("text/plain"));
        if (dragged) run("/functions/" + dragged + "/move", { parent_id: null });
      });
      const input = el("input", { type: "text", maxlength: 160, placeholder: "Nouvelle fonction : verbe + complément", "aria-label": "Nouvelle fonction hors arbre" });
      zone.append(el("form", { class: "dm-new", onsubmit: (ev) => { ev.preventDefault(); run("/functions", { text: input.value }, "post"); } },
        input, el("button", { type: "submit", class: "btn btn-small" }, "Ajouter hors arbre")));
    }
    return zone;
  }

  function card(f, state, select, editable, run) {
    const kids = D.children(state.data.functions, f.id);
    const node = el("button", { type: "button", class: "dm-card" + (f.id === state.selected ? " dm-selected" : "") + " dm-t-" + f.ftype,
      draggable: editable ? "true" : null, onclick: () => select(f.id) },
    el("span", { class: "dm-code" }, "F" + f.number), el("span", { class: "dm-text" }, f.text),
    el("span", { class: "muted dm-card-type" }, state.data.labels.types[f.ftype] + (kids.length ? " · " + kids.length + " comment" : "")));
    if (editable) D.dropTarget(node, f.id, (dragged, target) => run("/functions/" + dragged + "/move", { parent_id: target }), true);
    return node;
  }

  function listView(state) {
    const L = state.data.labels;
    const order = [];
    const walk = (f) => { order.push(f); D.children(state.data.functions, f.id).forEach(walk); };
    state.data.functions.filter((f) => f.is_primary).forEach(walk);
    state.data.functions.filter((f) => !f.in_tree && f.level === 1).forEach(walk);
    return DA.table(["Code", "Fonction", "Niveau", "Type", "Kano", "Importance", "Chemin critique"], order.map((f) => el("tr", null,
      el("td", { class: "nowrap" }, el("span", { class: "dm-code" }, "F" + f.number)),
      el("td", { class: "dm-indent-" + Math.min(f.level, 4) }, f.text),
      el("td", null, f.in_tree ? L.levels[f.level] : "Hors arbre"), el("td", null, L.types[f.ftype]),
      el("td", null, L.kano[f.kano] || "—"), el("td", null, L.importance[f.importance] || "—"),
      el("td", null, f.critical ? "Oui" : "—"))));
  }

  function ask(title, done) {
    const input = el("input", { type: "text", maxlength: 160, placeholder: "ex. Éclairer une surface de travail" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: (ev) => { ev.preventDefault(); close(); done(input.value); } },
      field("Fonction (verbe à l'infinitif + complément)", input,
        "Ce que le produit réalise, le plus simplement possible. Elle reçoit le numéro libre suivant (F1, F2…)."),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
        el("button", { type: "submit", class: "btn btn-primary" }, "Créer")));
    close = modal(title, form);
    input.focus();
  }

  function empty(ctx, run, editable) {
    return DA.spaces.startHere("Arbre fonctionnel de " + ctx.meta.project.name,
      "Commencez par la fonction primaire : ce que le produit réalise (verbe + complément). Ajoutez ensuite à sa droite les "
      + "fonctions secondaires, dans l'ordre de la première utilisation, puis leurs tertiaires. Ou racontez d'abord l'usage dans la "
      + "Storyline et demandez l'arbre à un assistant IA. L'exemple montre la méthode sur une lampe de bureau connectée.",
      editable ? [["Créer la fonction primaire", () => ask("Fonction primaire", (text) => run("/functions", { text, primary: true }, "post")), true],
        ["Depuis la Storyline, avec l'IA", () => { location.hash = A.href(ctx, "story"); }],  // 0.60.52 (D-O-061)
        ["Charger l'exemple : lampe de bureau", () => run("/example", { name: "lampe" })]] : []);
  }

  A.views.ftree = view;
})();
