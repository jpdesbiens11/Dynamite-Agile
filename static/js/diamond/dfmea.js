/* Diamond · « DFMEA » (0.60.15, D-O-027): #/diamond/KEY/dfmea. The Design FMEA of the product, AIAG-VDA structure, on
   the functions of the functional tree: the table (dfmea_table.js), the columns to show (presets or one by one, kept per
   browser), the AP filter, « Depuis l'arbre », « Depuis les risques », the example, the CSV export and the link to the
   legend of the Action Priority (dfmea_legend.js, #/diamond/KEY/dfmeaap). 0.61.0 (D-O-107): the classes CC / SC -- the
   columns « Class » and « Décision » (dfmea_class.js), the class filters, the rules and symbols (#/diamond/KEY/dfmeaclass). */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;
  const STORE = "diamond.dfmea.columns";
  const PRESETS = [
    ["Toutes", null],
    ["Structure et fonction", ["higher", "focus", "lower", "function_id", "requirement", "failure_mode"]],
    ["Chaîne de défaillance", ["focus", "function_id", "failure_mode", "effect", "severity", "class", "cause", "occurrence", "detection", "ap"]],
    ["Classes CC / SC", ["function_id", "requirement", "failure_mode", "effect", "severity", "class", "class_decision", "occurrence", "ap"]],  // 0.61.0
    ["Contrôles et cotation", ["failure_mode", "cause", "prevention", "occurrence", "detection_ctrl", "detection", "severity", "rpn", "ap", "action"]],
    ["Actions et suivi", ["function_id", "failure_mode", "ap", "action", "action_owner_id", "action_due", "action_status", "ticket"]],  // 0.60.38
  ];
  const LAMP = "Éclairer une surface de travail";
  // 0.61.0: a column added after a choice was kept in this browser is shown once (its choice did not know it)
  const SEEN = STORE + ".seen", BEFORE = ["class", "class_decision"];

  function loadVisible() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE) || "null");
      if (Array.isArray(saved) && saved.length) {
        const seen = JSON.parse(localStorage.getItem(SEEN) || "null") || D.DFMEA_COLS.map((c) => c.key).filter((k) => !BEFORE.includes(k));
        return new Set(saved.concat(D.DFMEA_COLS.map((c) => c.key).filter((k) => !seen.includes(k))));
      }
    } catch (err) { /* private window: all the columns */ }
    return new Set(D.DFMEA_COLS.map((c) => c.key));
  }
  function saveVisible(set) {
    try {
      localStorage.setItem(STORE, JSON.stringify([...set]));
      localStorage.setItem(SEEN, JSON.stringify(D.DFMEA_COLS.map((c) => c.key)));
    } catch (err) { /* not kept */ }
  }

  async function view(page, ctx) {
    const base = D.base(ctx) + "/dfmea";
    const state = { key: ctx.key, ctx, editable: A.canEdit(ctx), data: await api.get(base), visible: loadVisible(), ap: "", cls: "", focus: null };
    const holder = el("div", { class: "dm-page" });
    page.append(holder);
    const redraw = () => D.later(() => draw(holder, ctx, state, api_));
    const api_ = {
      act: async (path, body) => {
        try {
          const res = await api.post(base + path, body || {});
          state.data = res;
          if (res.completed) toast(D.completedText(res.completed), "success");
          else if (res.added !== undefined) toast(res.added ? res.added + " ligne(s) ajoutée(s)." : "Rien à ajouter : tout est déjà dans le DFMEA.", "success");
        } catch (err) { toast(err.message, "error"); }
        redraw();
      },
      save: async (id, key, value) => {
        const body = {};
        body[key] = ["function_id", "action_owner_id", "severity", "occurrence", "detection"].includes(key) ? (value ? Number(value) : null) : value;
        try {
          state.data = await api.patch(base + "/rows/" + id, body);
          const row = state.data.rows.find((r) => r.id === id);
          if (key === "test_id" || key.startsWith("action_")) { redraw(); return; }  // 0.60.24 key test; 0.60.38 late, status colours
          if (row) D.dfmeaRefreshRow(holder, row, state.data.labels.ap, state);  // 0.61.0: the class follows S and O
          D.classRefreshFilters(holder, state);
          drawChecks(holder, state);
        } catch (err) { toast(err.message, "error"); }
      },
    };
    state.redraw = redraw;
    state.track = async (id) => {  // 0.60.38 (D-O-047): « Suivre dans Agile »
      try {
        const res = await api.post(D.base(ctx) + "/actions/dfmea/" + id + "/track", {});
        state.data = res;
        toast("Ticket " + res.tracked + " créé dans Agile : son status devient celui de la ligne.", "success");
      } catch (err) { toast(err.message, "error"); }
      redraw();
    };
    draw(holder, ctx, state, api_);
  }

  function draw(holder, ctx, state, act) {
    clear(holder);
    const data = state.data, editable = A.canEdit(ctx);
    state.filtered = data.rows.filter((r) => (!state.ap || (state.ap === "none" ? !r.ap : r.ap === state.ap)) && D.classKeep(r, state.cls, data));
    holder.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "DFMEA")], [
      el("a", { class: "btn btn-small", href: A.href(ctx, "dfmeaap"), "data-new": "0.60.15-ap-legend" }, "Légende AP"),
      el("a", { class: "btn btn-small", href: A.href(ctx, "dfmeaclass"), "data-new": "0.61.0-class-rules" }, "Classes CC / SC"),
      data.rows.length ? el("a", { class: "btn btn-small", href: D.base(ctx) + "/dfmea/export.csv", download: "" }, "Exporter (.csv)") : null]),
    el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.15-dfmea" }, "DFMEA"),
      el("p", { class: "muted" }, "Design FMEA, structure AIAG-VDA, sur les fonctions de l'arbre fonctionnel : une ligne par chaîne de "
        + "défaillance — l'effet sur l'élément supérieur (S), le mode de défaillance de l'élément analysé, la cause dans l'élément "
        + "inférieur (O), les contrôles de prévention et de détection (D). RPN et Action Priority côte à côte.")),
    el("div", { class: "dm-legend dm-fm-levels" }, el("span", { class: "dm-fm-chip dm-fm-h-higher" }, "Higher-Level Element"),
      el("span", { class: "dm-fm-chip dm-fm-h-focus" }, "Focus Element"), el("span", { class: "dm-fm-chip dm-fm-h-lower" }, "Lower-Level Element"),
      el("span", { class: "dm-fm-chip dm-fm-h-score" }, "Scores : RPN et AP"),
      el("span", { class: "dm-fm-chip dm-fm-h-act", "data-new": "0.60.38-act" }, "Suivi de l'action : responsable, échéance, ticket"),
      el("span", { class: "dm-fm-chip dm-fm-h-special", "data-new": "0.61.0-class",
        "data-tip": "Liseré épais rouge : CC, orange : SC (pâle tant que la classe n'est que proposée) ; liseré fin : AP High ou Medium" },
      "Class : CC · SC, proposée par la règle, décidée par une personne")));
    if (!data.functions.length) {
      holder.append(DA.spaces.startHere("Construisez d'abord l'arbre fonctionnel", "Le DFMEA reprend exactement les fonctions de l'arbre : "
        + "sans fonction, il n'y a rien à analyser.", [["Ouvrir l'arbre fonctionnel", A.href(ctx, "ftree"), true]]));
      return;
    }
    holder.append(el("div", { class: "dm-fm-checks" }));
    drawChecks(holder, state);
    holder.append(toolbar(ctx, state, act, editable));
    if (!data.rows.length) {
      holder.append(DA.spaces.startHere("DFMEA de " + ctx.meta.project.name, "Partez de l'arbre : une ligne par fonction, puis, pour "
        + "chacune, comment elle peut faillir, avec quel effet et pourquoi. Les risques projet cochés « À détailler dans le DFMEA » "
        + "arrivent avec « Depuis les risques ».", editable ? [["Compléter le DFMEA", () => act.act("/complete", {}), true],
        ["Depuis l'arbre", () => act.act("/from-tree", {})],
        ["Nouvelle ligne", () => act.act("/rows", {})],
        data.functions.some((f) => f.text === LAMP) ? ["Charger le DFMEA de l'exemple", () => act.act("/example", {})] : null] : []));
      return;
    }
    const onKey = (ev, row, col) => {
      if (!ev.altKey || (ev.key !== "ArrowUp" && ev.key !== "ArrowDown") || !editable) return;
      ev.preventDefault();
      state.focus = { row: row.id, col: col.key };
      act.act("/rows/" + row.id + "/move", { direction: ev.key === "ArrowUp" ? "up" : "down" });
    };
    holder.append(D.classFilters(state), D.dfmeaTable({ state, visible: state.visible, editable, save: act.save, act: act.act, onKey }));  // 0.61.0
    if (!state.filtered.length) holder.append(el("p", { class: "muted dm-fm-nomatch" }, "Aucune ligne ne correspond aux filtres : choisissez « Toutes »."));
    if (state.focus) {
      const f = state.focus;
      state.focus = null;
      setTimeout(() => { const n = holder.querySelector('[data-row="' + f.row + '"][data-col="' + f.col + '"]'); if (n) n.focus(); }, 0);
    }
  }

  function drawChecks(holder, state) {
    const box = holder.querySelector(".dm-fm-checks");
    if (!box) return;
    clear(box);
    const checks = state.data.checks;
    box.append(!checks.length ? el("p", { class: "dm-advice-ok" }, "Chaque fonction est analysée, chaque ligne est cotée, chaque AP High a son action.")
      : el("details", { class: "dm-advice", open: true, "data-new": "0.60.15-checks" }, el("summary", null, "Conseils de la méthode (" + checks.length + ")"),
        el("ul", null, checks.map((c) => el("li", null, c)))));
  }

  function toolbar(ctx, state, act, editable) {
    const hidden = D.DFMEA_COLS.length - state.visible.size;
    const chooser = el("details", { class: "dm-fm-cols", "data-new": "0.60.15-columns" }, el("summary", null, "Colonnes" + (hidden ? " (" + hidden + " masquée(s))" : "")),
      el("div", { class: "dm-actions" }, PRESETS.map(([label, keys]) => el("button", { type: "button", class: "btn btn-small", onclick: () => {
        state.visible = new Set(keys || D.DFMEA_COLS.map((c) => c.key));
        saveVisible(state.visible);
        state.redraw();
      } }, label))),
      el("div", { class: "dm-fm-colgrid" }, D.DFMEA_COLS.map((c) => {
        const box = el("input", { type: "checkbox", checked: state.visible.has(c.key) });
        box.dataset.col = c.key;  // 0.60.26: ticked together, applied on « Appliquer » or a click outside (DA.choiceBatch)
        return el("label", { class: "dm-check dm-fm-colpick dm-fm-h-" + c.group }, box, " " + c.label);
      })));
    chooser.open = !!state.colsOpen;
    chooser.addEventListener("toggle", () => { state.colsOpen = chooser.open; });
    DA.choiceBatch(chooser, (list) => {
      list.forEach((i) => { if (i.checked) state.visible.add(i.dataset.col); else state.visible.delete(i.dataset.col); });
      if (!state.visible.size) state.visible.add("failure_mode");
      saveVisible(state.visible);
      state.colsOpen = false;
      state.redraw();
    });
    const ap = el("select", { "aria-label": "Filtrer par AP" }, [["", "Toutes les lignes"], ["H", "AP High"], ["M", "AP Medium"], ["L", "AP Low"], ["none", "Sans AP"]]
      .map(([k, label]) => el("option", { value: k, selected: state.ap === k }, label)));
    ap.addEventListener("change", () => { state.ap = ap.value; state.redraw(); });
    return el("div", { class: "dm-fm-toolbar" }, editable ? el("div", { class: "dm-actions" },
      el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => act.act("/rows", {}) }, "Nouvelle ligne"),
      el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.28-dfmea-complete", "data-tip": "Une ligne pour chaque fonction de l'arbre "
        + "sans ligne, l'essai clé le plus pertinent de la Test Base et les bonnes pratiques de l'industrie en prévention",
      onclick: () => act.act("/complete", {}) }, "Compléter le DFMEA"),
      el("button", { type: "button", class: "btn btn-small", "data-tip": "Une ligne par fonction de la vue détaillée pas encore analysée", onclick: () => act.act("/from-tree", {}) }, "Depuis l'arbre"),
      el("button", { type: "button", class: "btn btn-small", "data-tip": "Les risques projet cochés « À détailler dans le DFMEA »",
        onclick: () => act.act("/from-risks", {}) }, "Depuis les risques")) : null, ap, chooser);
  }

  A.views.dfmea = view;
})();
