/* Diamond · « Analyse de risque projet » (0.60.14, D-O-026): #/diamond/KEY/prisk. The high-level register of the
   project risks, before the DFMEA: a 5 x 5 heat map (probability x impact, now or residual) whose cells filter the
   register, the register sorted by score, the panel of one risk, the method's advice and the CSV export. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;
  const LAMP = "Éclairer une surface de travail";

  async function view(page, ctx) {
    const base = D.base(ctx);
    const state = { data: await api.get(base + "/risks"), selected: null, creating: false, cell: null, residual: false,
      status: "live", category: "" };
    const holder = el("div", { class: "dm-page" });
    page.append(holder);
    const run = async (path, body, method) => {
      try {
        const res = await api[method || "post"](base + path, body || {});
        state.data = res;
        if (res.created) { state.selected = res.created; state.creating = false; }
        if (path.endsWith("/archive")) state.selected = null;
        if (method === "patch") toast("Risque enregistré.", "success");
      } catch (err) { toast(err.message, "error"); }
      D.later(() => draw(holder, ctx, state, run));
    };
    state.redraw = () => D.later(() => draw(holder, ctx, state, run));
    draw(holder, ctx, state, run);
  }

  function filtered(state) {
    return state.data.risks.filter((r) => (state.status === "all" || (state.status === "live" ? r.status !== "closed" : r.status === state.status))
      && (!state.category || r.category === state.category)
      && (!state.cell || (state.residual ? [r.residual_p, r.residual_i] : [r.probability, r.impact]).join(":") === state.cell))
      .sort((a, b) => b.score - a.score || a.number - b.number);
  }

  function draw(holder, ctx, state, run) {
    clear(holder);
    const data = state.data, editable = A.canEdit(ctx);
    holder.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Risques projet")], [
      data.risks.length ? el("a", { class: "btn btn-small", href: D.base(ctx) + "/risks/export.csv", download: "" }, "Exporter (.csv)") : null,
      editable ? el("button", { type: "button", class: "btn btn-primary btn-small", "data-new": "0.60.14-new-risk",
        onclick: () => { state.creating = true; state.selected = null; state.redraw(); } }, "Nouveau risque") : null]),
    el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.14-prisk" }, "Analyse de risque projet"),
      el("p", { class: "muted" }, "Les risques du projet, vus de haut, avant le DFMEA : « Si <cause>, alors <événement>, ce qui "
        + "<conséquence> ». Probabilité × impact de 1 à 5, une stratégie, une action, un responsable, puis le risque résiduel. Les "
        + "risques techniques se détaillent ensuite dans le DFMEA, fonction par fonction.")));
    if (!data.risks.length && !state.creating) {
      holder.append(DA.spaces.startHere("Registre de risques de " + ctx.meta.project.name,
        "Réunissez l'équipe 20 minutes : qu'est-ce qui pourrait empêcher le projet d'aboutir ? Technique, délais, coûts, équipe, "
        + "fournisseurs, normes, marché, sécurité. Une ligne par risque, puis on les classe sur la carte.",
        editable ? [["Nouveau risque", () => { state.creating = true; state.redraw(); }, true],
          data.functions.some((f) => f.text === LAMP) ? ["Charger les risques de l'exemple", () => run("/risks/example", {})] : null] : []));
      return;
    }
    holder.append(advice(data.checks));
    const chosen = data.risks.find((r) => r.id === state.selected);
    const close = () => { state.selected = null; state.creating = false; state.redraw(); };
    const left = el("div", { class: "dm-rk-left" }, heatmap(state), filters(state), register(state));
    holder.append(state.creating || chosen
      ? el("div", { class: "dm-work dm-with-panel" }, left, D.riskPanel(state, state.creating ? null : chosen, run, editable, close))
      : left);
  }

  function heatmap(state) {
    const L = state.data.labels;
    const counts = {};
    state.data.risks.filter((r) => r.status !== "closed").forEach((r) => {
      const k = (state.residual ? [r.residual_p, r.residual_i] : [r.probability, r.impact]).join(":");
      counts[k] = (counts[k] || 0) + 1;
    });
    const grid = el("div", { class: "dm-heat", role: "grid", "aria-label": "Carte des risques : probabilité × impact" });
    grid.append(el("span", { class: "dm-heat-axis dm-heat-y" }, "Probabilité ↑"));
    for (let p = 5; p >= 1; p--) {
      grid.append(el("span", { class: "dm-heat-tick" }, String(p)));
      for (let i = 1; i <= 5; i++) {
        const k = p + ":" + i, n = counts[k] || 0, lv = L.levels.find((l) => p * i >= l.min);
        grid.append(el("button", { type: "button", class: "dm-heat-cell dm-lv-" + lv.key + (state.cell === k ? " dm-heat-on" : ""),
          "aria-label": "Probabilité " + p + ", impact " + i + " : " + n + " risque(s)", "data-tip": D.P_WORDS[p] + " × " + D.I_WORDS[i],
          onclick: () => { state.cell = state.cell === k ? null : k; state.redraw(); } }, n ? String(n) : ""));
      }
    }
    grid.append(el("span", null), ...[1, 2, 3, 4, 5].map((i) => el("span", { class: "dm-heat-tick" }, String(i))));
    const toggle = el("div", { class: "subtabs dm-heat-mode" }, [[false, "Maintenant"], [true, "Après les actions (résiduel)"]].map(([v, label]) =>
      el("a", { href: "#", class: "subtab" + (state.residual === v ? " active" : ""), "data-new": v ? "0.60.14-residual-map" : null,
        onclick: (ev) => { ev.preventDefault(); state.residual = v; state.cell = null; state.redraw(); } }, label)));
    return el("section", { class: "dm-heat-box" }, toggle, grid, el("p", { class: "muted dm-heat-x" }, "Impact →"),
      el("div", { class: "dm-legend" }, L.levels.slice().reverse().map((l) => el("span", { class: "dm-score dm-lv-" + l.key }, l.label))),
      state.cell ? el("button", { type: "button", class: "btn btn-small", onclick: () => { state.cell = null; state.redraw(); } },
        "Voir tous les risques") : null);
  }

  function filters(state) {
    const L = state.data.labels;
    const status = el("select", { "aria-label": "Status" }, [["live", "Ouverts et en traitement"], ["all", "Tous"]].concat(Object.entries(L.statuses))
      .map(([k, label]) => el("option", { value: k, selected: state.status === k }, label)));
    status.addEventListener("change", () => { state.status = status.value; state.redraw(); });
    const cat = el("select", { "aria-label": "Catégorie" }, [["", "Toutes les catégories"]].concat(Object.entries(L.categories))
      .map(([k, label]) => el("option", { value: k, selected: state.category === k }, label)));
    cat.addEventListener("change", () => { state.category = cat.value; state.redraw(); });
    return el("div", { class: "dm-actions dm-rk-filters" }, status, cat);
  }

  /* with the panel open, the register keeps only the columns that fit beside it */
  function register(state) {
    const L = state.data.labels, list = filtered(state);
    const compact = !!(state.selected || state.creating);
    if (!list.length) return el("p", { class: "muted" }, "Aucun risque avec ces filtres.");
    const heads = compact ? ["Code", "Risque", "Score", "Status", "Résiduel"]
      : ["Code", "Risque", "Catégorie", "P", "I", "Score", "Stratégie", "Responsable", "Échéance", "Status", "Résiduel"];
    return DA.table(heads, list.map((r) => {
        const cells = {
          code: el("td", { class: "nowrap" }, el("span", { class: "dm-code" }, "R-" + r.number), r.to_dfmea ? el("span", { class: "badge badge-info dm-rk-dfmea" }, "DFMEA") : null),
          title: el("td", null, r.title, r.function_number ? el("span", { class: "muted dm-rk-fn" }, " · F" + r.function_number) : null),
          score: el("td", null, D.riskScoreBadge(L, r.probability, r.impact)), status: el("td", null, L.statuses[r.status]),
          residual: el("td", null, D.riskScoreBadge(L, r.residual_p, r.residual_i)) };
        const row = el("tr", { class: "dm-rk-row" + (r.id === state.selected ? " dm-rk-sel" : ""), tabindex: "0" }, compact
          ? [cells.code, cells.title, cells.score, cells.status, cells.residual]
          : [cells.code, cells.title, el("td", null, L.categories[r.category] || r.category), el("td", null, String(r.probability)),
            el("td", null, String(r.impact)), cells.score, el("td", null, L.responses[r.response] && r.response ? L.responses[r.response] : "—"),
            el("td", null, r.owner_name || "—"), el("td", { class: "nowrap" }, r.due_date || "—"), cells.status, cells.residual]);
        const open = () => { state.selected = r.id; state.creating = false; state.redraw(); };
        row.addEventListener("click", open);
        row.addEventListener("keydown", (ev) => { if (ev.key === "Enter") open(); });
        return row;
      }));
  }

  function advice(checks) {
    if (!checks.length) return el("p", { class: "dm-advice-ok" }, "Le registre est complet : chaque risque élevé a son action et son responsable.");
    return el("details", { class: "dm-advice", open: true, "data-new": "0.60.14-checks" },
      el("summary", null, "Conseils de la méthode (" + checks.length + ")"), el("ul", null, checks.map((c) => el("li", null, c))));
  }

  A.views.prisk = view;
})();
