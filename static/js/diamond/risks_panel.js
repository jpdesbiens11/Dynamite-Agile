/* Diamond · Analyse de risque projet: the form of one risk (0.60.14). « Si <cause>, alors <événement>, ce qui
   <conséquence> »; probability and impact 1-5 with their words, the score and its level as they change; response, action,
   owner, due date, status; residual risk; the function of the tree it concerns and « À détailler dans le DFMEA ». */
(function () {
  "use strict";

  const { el, field } = DA;
  const P_WORDS = { 1: "1 · Rare", 2: "2 · Peu probable", 3: "3 · Possible", 4: "4 · Probable", 5: "5 · Presque certain" };
  const I_WORDS = { 1: "1 · Négligeable", 2: "2 · Mineur", 3: "3 · Modéré", 4: "4 · Majeur", 5: "5 · Critique" };

  function select(options, value, empty) {
    const entries = Object.entries(options);
    return el("select", null, (empty ? [["", empty]] : []).concat(entries).map(([k, label]) =>
      el("option", { value: k, selected: String(k) === String(value == null ? "" : value) }, label)));
  }

  function levelOf(labels, score) {
    const lv = labels.levels.find((l) => score >= l.min);
    return lv ? lv : { key: "none", label: "—" };
  }

  function scoreBadge(labels, p, i) {
    const s = p && i ? p * i : 0;
    const lv = levelOf(labels, s);
    return el("span", { class: "dm-score dm-lv-" + lv.key }, s ? s + " · " + lv.label : "—");
  }

  /* risk: an existing risk, or null for a new one. run(path, body, method) -> saves and redraws. */
  function panel(state, risk, run, editable, close) {
    const L = state.data.labels;
    const r = risk || { title: "", cause: "", consequence: "", category: "technique", phase: "", probability: 3, impact: 3, response: "",
      action: "", owner_id: null, due_date: "", status: "open", residual_p: null, residual_i: null, function_id: null, to_dfmea: 0, notes: "" };
    const head = el("div", { class: "dm-panel-head" }, el("strong", null, risk ? "R-" + risk.number : "Nouveau risque"),
      el("button", { type: "button", class: "btn btn-small", onclick: close }, "Fermer"));
    const box = el("aside", { class: "dm-panel", "aria-label": risk ? "Risque R-" + risk.number : "Nouveau risque" }, head);
    if (!editable) {
      box.append(el("p", null, el("strong", null, r.title)), el("p", null, "Si " + (r.cause || "…") + ", alors " + r.title.toLowerCase()
        + (r.consequence ? ", ce qui " + r.consequence : "") + "."), scoreBadge(L, r.probability, r.impact),
      r.action ? el("p", null, el("strong", null, "Action : "), r.action) : null);
      return box;
    }
    const title = el("input", { type: "text", maxlength: 200, value: r.title, placeholder: "ex. Surchauffe des DEL dans la tête" });
    const cause = el("textarea", { rows: 2, maxlength: 400, placeholder: "Si… (la cause)" }, r.cause);
    const cons = el("textarea", { rows: 2, maxlength: 400, placeholder: "…ce qui (la conséquence pour le projet)" }, r.consequence);
    const category = select(L.categories, r.category), phase = select(L.phases, r.phase);
    const p = select(P_WORDS, r.probability), i = select(I_WORDS, r.impact);
    const live = el("p", { class: "dm-score-line" }, "Score P × I : ", scoreBadge(L, r.probability, r.impact));
    const rp = select(P_WORDS, r.residual_p, "—"), ri = select(I_WORDS, r.residual_i, "—");
    rp.setAttribute("data-new", "0.60.14-residual");
    const liveRes = el("p", { class: "dm-score-line" }, "Résiduel : ", scoreBadge(L, r.residual_p, r.residual_i));
    const refresh = () => {
      live.replaceChild(scoreBadge(L, Number(p.value), Number(i.value)), live.lastChild);
      liveRes.replaceChild(scoreBadge(L, Number(rp.value), Number(ri.value)), liveRes.lastChild);
    };
    [p, i, rp, ri].forEach((s) => s.addEventListener("change", refresh));
    const response = select(L.responses, r.response);
    const action = el("textarea", { rows: 2, maxlength: 600, placeholder: "Ce qu'on fait, et quand on saura que ça a marché" }, r.action);
    const owner = select(Object.fromEntries(state.data.members.map((m) => [m.id, m.display_name])), r.owner_id, "— personne —");
    const due = el("input", { type: "date", value: r.due_date || "" });
    const status = select(L.statuses, r.status);
    const fn = select(Object.fromEntries(state.data.functions.map((f) => [f.id, "F" + f.number + " " + f.text])), r.function_id, "— aucune —");
    const dfmea = el("input", { type: "checkbox", checked: !!r.to_dfmea });
    const notes = el("textarea", { rows: 2, maxlength: 2000 }, r.notes || "");
    const body = () => ({ title: title.value, cause: cause.value, consequence: cons.value, category: category.value, phase: phase.value,
      probability: Number(p.value), impact: Number(i.value), response: response.value, action: action.value,
      owner_id: owner.value ? Number(owner.value) : null, due_date: due.value, status: status.value,
      residual_p: rp.value ? Number(rp.value) : "", residual_i: ri.value ? Number(ri.value) : "",
      function_id: fn.value ? Number(fn.value) : null, to_dfmea: dfmea.checked, notes: notes.value });
    box.append(el("form", { class: "ag-form dm-form", onsubmit: (ev) => {
      ev.preventDefault();
      if (risk) run("/risks/" + risk.id, body(), "patch"); else run("/risks", body(), "post");
    } },
    field("Risque (l'événement)", title), field("Cause : si…", cause), field("Conséquence : ce qui…", cons),
    el("div", { class: "dm-row" }, field("Catégorie", category), field("Phase du PDP", phase)),
    el("div", { class: "dm-row" }, field("Probabilité", p), field("Impact", i)), live,
    el("div", { class: "dm-row" }, field("Stratégie", response), field("Status", status)),
    field("Action", action),
    el("div", { class: "dm-row" }, field("Responsable", owner), field("Échéance", due)),
    el("div", { class: "dm-row" }, field("Probabilité résiduelle", rp), field("Impact résiduel", ri)), liveRes,
    field("Fonction de l'arbre concernée", fn),
    el("label", { class: "dm-check", "data-new": "0.60.14-to-dfmea" }, dfmea, " À détailler dans le DFMEA"),
    field("Notes", notes),
    el("div", { class: "form-actions" }, el("button", { type: "submit", class: "btn btn-primary btn-small" }, risk ? "Enregistrer" : "Créer le risque"))));
    if (risk) {
      box.append(el("div", { class: "dm-actions dm-move" },
        el("button", { type: "button", class: "btn btn-small", onclick: () => run("/risks/" + risk.id + "/duplicate", {}) }, "Dupliquer"),
        el("button", { type: "button", class: "btn btn-small btn-danger", onclick: () => {
          if (window.confirm("Archiver R-" + risk.number + " « " + risk.title + " » ? Le numéro R-" + risk.number
            + " ne sera jamais redonné. L'action est journalisée.")) run("/risks/" + risk.id + "/archive", {});
        } }, "Archiver")));
    }
    title.focus();
    return box;
  }

  DA.diamond = Object.assign(DA.diamond || {}, { riskPanel: panel, riskScoreBadge: scoreBadge, P_WORDS, I_WORDS });
})();
