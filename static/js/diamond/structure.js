/* Diamond · « Structure fonctionnelle » (0.60.13, D-O-025): #/diamond/KEY/fstructure. The boundary diagram built from the
   functional tree: « Vue générale » (the secondary functions as sub-systems) and « Vue détaillée » (the tertiary
   functions in the frame of their sub-system), inputs on the left, outputs on the right, energy / material /
   information flows with the legend of the course, the method's advice, drag and link. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;
  const LEGEND = [["energy", "Énergie"], ["material", "Matière"], ["information", "Information"]];

  async function view(page, ctx) {
    const base = D.base(ctx) + "/structure";
    const state = { data: await api.get(base), view: "general", selected: null, link: null, labels: { general: true, detail: false },
      showParts: true, editing: null };
    const holder = el("div", { class: "dm-page" });
    page.append(holder);
    const redraw = () => D.later(() => draw(holder, ctx, state, run));
    const run = async (path, body, method) => {
      try {
        state.data = await api[method || "post"](base + path, body || {});
        if (path.endsWith("/delete")) state.selected = null;
      } catch (err) { toast(err.message, "error"); }
      state.link = null;
      redraw();
    };
    state.redraw = redraw;
    draw(holder, ctx, state, run);
  }

  function saved(state) {
    const out = new Map();
    state.data.positions.filter((p) => p.view === state.view).forEach((p) => {
      out.set(p.port_id ? D.structureKey("port", p.port_id) : D.structureKey("function", p.function_id), { x: p.x, y: p.y });
    });
    return out;
  }

  function draw(holder, ctx, state, run) {
    clear(holder);
    const data = state.data;
    const editable = A.canEdit(ctx);
    holder.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Structure fonctionnelle")]),
      el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.13-fstructure" }, "Structure fonctionnelle"),
        el("p", { class: "muted" }, "Le boundary diagram du produit, tiré de l'arbre fonctionnel : les entrées du système à gauche, "
          + "les sorties à droite, et entre les deux les flux d'énergie, de matière et d'information. D'abord la vue générale "
          + "(les fonctions secondaires deviennent les sous-systèmes), puis la vue détaillée (leurs fonctions tertiaires).")));
    if (!data.secondaries.length) {
      holder.append(DA.spaces.startHere("Construisez d'abord l'arbre fonctionnel",
        "La structure reprend les fonctions secondaires et tertiaires de l'arbre. Sans fonction secondaire, il n'y a rien à relier.",
        [["Ouvrir l'arbre fonctionnel", A.href(ctx, "ftree"), true]]));
      return;
    }
    holder.append(tabs(state));
    if (state.view === "parts") {  // 0.60.20 (D-O-031): the matrix parts x functions instead of the diagram
      holder.append(D.partsView(state, run, editable));
      return;
    }
    holder.append(legend());
    if (!data.ports.length && !data.flows.length && editable) {
      holder.append(el("div", { class: "dm-advice" }, el("p", null, "Structure vide. Ajoutez les entrées et sorties du système dans le "
        + "panneau, puis reliez les blocs. Si cet arbre est celui de l'exemple (lampe de bureau), sa structure peut être chargée."),
      el("button", { type: "button", class: "btn btn-small", onclick: () => run("/example", {}) }, "Charger la structure de l'exemple")));
    }
    holder.append(advice(data.checks));
    if (state.link) {
      holder.append(el("p", { class: "dm-st-linkbar", role: "status" }, "Cliquez le bloc d'arrivée du flux… ",
        el("button", { type: "button", class: "btn btn-small", onclick: () => { state.link = null; state.redraw(); } }, "Annuler")));
    }
    const onSelect = (sel) => {
      if (state.link && sel.type !== "flow") {
        if (sel.key !== D.structureKey(state.link.src.type, state.link.src.id)) {
          run("/flows", Object.assign({}, state.link, { dst: { type: sel.type, id: sel.id } }));
          return;
        }
      }
      const same = state.selected && state.selected.type === sel.type && state.selected.id === sel.id;
      state.selected = same ? null : sel;
      state.redraw();
    };
    const onMove = (b) => {
      const pos = { view: state.view, function_id: b.type === "function" ? b.id : null, port_id: b.type === "port" ? b.id : null, x: b.x, y: b.y };
      state.data.positions = state.data.positions.filter((p) => !(p.view === pos.view && p.function_id === pos.function_id && p.port_id === pos.port_id)).concat([pos]);
      api.put(D.base(ctx) + "/structure/position", { view: state.view, node: { type: b.type, id: b.id }, x: b.x, y: b.y })
        .catch((err) => toast(err.message, "error"));
    };
    const flows = data.flows.filter((fl) => fl.view === state.view);
    const diagram = D.structureDraw({ data, view: state.view, saved: saved(state), selected: state.selected,
      link: state.link ? { key: D.structureKey(state.link.src.type, state.link.src.id) } : null, editable, onSelect, onMove, flows,
      showLabels: state.labels[state.view], parts: state.showParts ? D.partsByFunction(data, state.view) : null });
    const startLink = (body) => { state.link = body; state.redraw(); };
    const showLabels = el("input", { type: "checkbox", checked: state.labels[state.view] });
    showLabels.addEventListener("change", () => { state.labels[state.view] = showLabels.checked; state.redraw(); });
    const showParts = el("input", { type: "checkbox", checked: state.showParts });
    showParts.addEventListener("change", () => { state.showParts = showParts.checked; state.redraw(); });
    holder.append(el("div", { class: "dm-actions dm-st-tools" }, el("label", { class: "dm-check", "data-new": "0.60.13-labels" }, showLabels,
      " Libellés des flux (sinon : ceux du bloc choisi)"),
    data.parts.length ? el("label", { class: "dm-check", "data-new": "0.60.20-part-tags" }, showParts, " Pièces sur les blocs") : null,
    editable ? el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.13-layout",
      onclick: () => { if (window.confirm("Replacer tous les blocs de cette vue automatiquement ?")) run("/layout/reset", { view: state.view }); } },
    "Replacer automatiquement") : null));
    // the panel stands beside the diagram for a selection; otherwise its forms go below, and the diagram takes the width
    holder.append(state.selected ? el("div", { class: "dm-work dm-with-panel" }, diagram, D.structurePanel(state, run, editable, startLink))
      : el("div", { class: "dm-st-full" }, diagram, D.structurePanel(state, run, editable, startLink)));
  }

  function tabs(state) {
    const go = (k) => (ev) => { ev.preventDefault(); state.view = k; state.selected = null; state.link = null; state.editing = null; state.redraw(); };
    const tab = (k, label) => el("a", { href: "#", class: "subtab" + (k === state.view ? " active" : ""),
      "aria-current": k === state.view ? "page" : null, onclick: go(k), "data-new": k === "parts" ? "0.60.20-parts-tab" : null }, label);
    return el("nav", { class: "subtabs dm-st-views", "aria-label": "Vues" },
      Object.entries(state.data.labels.views).map(([k, label]) => tab(k, label + " · " + state.data.flows.filter((f) => f.view === k).length + " flux")),
      tab("parts", "Pièces × fonctions · " + state.data.parts.length + " pièce" + (state.data.parts.length > 1 ? "s" : "")));
  }

  function legend() {
    return el("div", { class: "dm-legend", "aria-label": "Légende" }, el("span", { class: "dm-axis" }, "Entrées du système →"),
      LEGEND.map(([k, label]) => el("span", { class: "dm-key dm-key-" + k }, label)), el("span", { class: "dm-axis" }, "→ Sorties du système"));
  }

  function advice(checks) {
    if (!checks.length) return el("p", { class: "dm-advice-ok" }, "La structure suit la méthode : chaque bloc échange un flux, et la vue "
      + "détaillée reprend les flux de la vue générale.");
    return el("details", { class: "dm-advice", open: true, "data-new": "0.60.13-checks" },
      el("summary", null, "Conseils de la méthode (" + checks.length + ")"), el("ul", null, checks.map((c) => el("li", null, c))));
  }

  A.views.fstructure = view;
})();
