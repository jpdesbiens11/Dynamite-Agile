/* Diamond · DFMEA: the classes CC / SC of the Space (0.60.101, D-O-108), #/diamond/KEY/dfmeaclass -- a page of its own
   (taller than a dialog may be): what CC and SC mean (AIAG, IATF 16949 § 8.3.3.3), the rule that proposes them (set per
   Space: S for a CC, S and O for a SC), the customer of the Space and the dictionary that turns the internal class into
   the customer's symbol on screen and in the exports. Start values: generic AIAG, Ford, aerospace AS9100 / AS9103; the
   symbols of any other customer are written by the team from its CSR, never assumed. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;
  const cpk = (x) => (x == null ? "—" : Number(x).toFixed(2).replace(".", ","));  // 0.60.102 (D-O-110)
  const COLS = [["cc_dfmea", "CC au DFMEA"], ["sc_dfmea", "SC au DFMEA"], ["cc_symbol", "CC au procédé"], ["sc_symbol", "SC au procédé"]];

  async function view(page, ctx) {
    const base = D.base(ctx) + "/dfmea/classes";
    const state = { ctx, base, editable: A.canEdit(ctx), data: await api.get(base) };
    const holder = el("div", { class: "dm-page dm-cls-page" });
    page.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("a", { href: A.href(ctx, "dfmea") }, "DFMEA"), el("span", null, "Classes CC / SC")]), holder);
    state.redraw = () => D.later(() => draw(holder, state));
    draw(holder, state);
  }

  async function send(state, method, path, body, done) {
    try {
      state.data = await api[method](state.base + path, body || {});
      if (done) toast(done, "success");
    } catch (err) { toast(err.message, "error"); return false; }
    state.redraw();
    return true;
  }

  function draw(holder, state) {
    clear(holder);
    const ctx = state.ctx, d = state.data;
    holder.append(el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.101-class-page" }, "Classes CC / SC"),
      el("p", { class: "muted" }, "Les caractéristiques spéciales au sens de l'AIAG et de l'IATF 16949 (§ 8.3.3.3). La plateforme propose une "
        + "classe à partir de la sévérité et de l'occurrence de chaque ligne du DFMEA ; une personne la confirme ou la refuse, avec sa "
        + "justification. Rien ne devient CC tout seul.")),
    el("div", { class: "dm-cls-cards" },
      card("CC", "Critical Characteristic", "Touche la sécurité ou la loi. Capabilité habituelle : Cpk d'au moins 1,67 ; traçabilité à long "
        + "terme (lot, numéro de série, résultat)."),
      card("SC", "Significant Characteristic", "Touche l'ajustement, la fonction, la performance ou la satisfaction du client. Capabilité "
        + "habituelle : Cpk d'au moins 1,33."),
      card("", "Chaque client, ses règles", "Les seuils et les symboles sont des paramètres du Space, pas du code : ils se règlent ici, "
        + "d'après les CSR (Customer-Specific Requirements) du client.")),
    rules(state), customers(state),
    el("div", { class: "dm-actions" }, el("a", { class: "btn btn-primary", href: A.href(ctx, "dfmea") }, "← Retour au DFMEA"),
      el("a", { class: "btn", href: A.href(ctx, "dfmeaap") }, "Légende AP")));
  }

  function card(code, title, text) {
    return el("section", { class: "dm-cls-card" }, el("h2", null, code ? el("span", { class: "dm-cls dm-cls-" + code }, code) : null, " " + title), el("p", null, text));
  }

  function num(value, labelText) {
    return el("input", { type: "number", min: 1, max: 10, step: 1, value, class: "dm-cls-num", "aria-label": labelText });
  }

  function rules(state) {
    const r = state.data.rules, n = state.data.proposed || {};
    const cc = num(r.cc_severity, "Sévérité qui propose une CC"), sc = num(r.sc_severity, "Sévérité la plus basse d'une SC"),
      so = num(r.sc_occurrence, "Occurrence qui propose une SC");
    [cc, sc, so].forEach((i) => { i.disabled = !state.editable; });
    const upper = el("strong", null, String(r.cc_severity - 1));
    cc.addEventListener("input", () => { upper.textContent = String((Number(cc.value) || 1) - 1); });
    return el("section", { class: "dm-cls-rules", "data-new": "0.60.101-class-thresholds" }, el("h2", null, "Règle de proposition du Space"),
      el("p", { class: "dm-cls-rule" }, el("span", { class: "dm-cls dm-cls-CC" }, "CC"), " proposée si S ≥ ", cc, " — la sévérité seule suffit."),
      el("p", { class: "dm-cls-rule" }, el("span", { class: "dm-cls dm-cls-SC" }, "SC"), " proposée si S de ", sc, " à ", upper, " et O ≥ ", so,
        " — règle de départ inspirée de Ford (YC, YS)."),
      el("p", { class: "muted" }, "Avec la règle enregistrée : " + (n.CC || 0) + " CC et " + (n.SC || 0) + " SC proposée(s) attendent une décision ; "
        + state.data.counts.special + " ligne(s) ont une classe confirmée. Changer la règle ne change aucune décision déjà prise."),
      state.editable ? el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => send(state, "patch", "",
        { cc_severity: Number(cc.value), sc_severity: Number(sc.value), sc_occurrence: Number(so.value) }, "Règle enregistrée.") }, "Enregistrer la règle") : null);
  }

  function customers(state) {
    const d = state.data;
    const rows = d.customers.map((c) => {
      const radio = el("input", { type: "radio", name: "dm-cls-customer", value: c.code, checked: c.code === d.rules.customer,
        disabled: !state.editable, "aria-label": "Client du Space : " + c.name });
      radio.addEventListener("change", () => send(state, "patch", "", { customer: c.code }, "Client du Space : " + c.name + "."));
      return el("tr", { class: c.code === d.rules.customer ? "dm-cls-active" : null },
        el("td", null, radio), el("td", null, el("strong", null, c.name), c.edited && c.preset ? el("span", { class: "muted" }, " (modifié)") : null),
        COLS.map(([k]) => el("td", { class: "dm-cls-symcell" }, el("span", { class: "dm-cls dm-cls-" + k.slice(0, 2).toUpperCase() }, c[k]))),
        el("td", { class: "dm-cls-labels" }, el("div", null, "CC : " + c.cc_label), el("div", null, "SC : " + c.sc_label)),
        el("td", { class: "nowrap", "data-new": "0.60.102-class-cpk" }, el("div", null, "CC " + cpk(c.cc_cpk)), el("div", null, "SC " + cpk(c.sc_cpk))),
        el("td", { class: "dm-cls-source" }, c.source),
        el("td", null, state.editable ? el("div", { class: "dm-actions" },
          el("button", { type: "button", class: "btn btn-small", onclick: () => edit(state, c) }, "Modifier"),
          c.preset && c.edited ? el("button", { type: "button", class: "btn btn-small", onclick: () => {
            if (window.confirm("Rétablir les valeurs de départ de « " + c.name + " » ? L'action est journalisée.")) send(state, "post", "/customers/" + c.code + "/delete", {}, "Valeurs de départ rétablies.");
          } }, "Rétablir") : null,
          !c.preset ? el("button", { type: "button", class: "btn btn-small", disabled: c.code === d.rules.customer, onclick: () => {
            if (window.confirm("Retirer « " + c.name + " » du dictionnaire ? L'action est journalisée.")) send(state, "post", "/customers/" + c.code + "/delete", {}, "Client retiré.");
          } }, "Retirer") : null) : null));
    });
    return el("section", { class: "dm-cls-dict", "data-new": "0.60.101-class-symbols" }, el("h2", null, "Client du Space et ses symboles"),
      el("p", { class: "muted" }, "La classe reste interne (CC, SC) ; le client coché donne le symbole affiché dans le DFMEA et dans les "
        + "exports. Ford, par exemple, écrit YC / YS au DFMEA, puis CC ∇ / SC au procédé. Les symboles des autres donneurs d'ordres ne sont "
        + "pas fournis : ajoutez votre client à partir de ses CSR, sans les deviner."),
      el("div", { class: "dm-scroll" }, el("table", { class: "data dm-cls-table" },
        el("thead", null, el("tr", null, el("th", { scope: "col" }, "Space"), el("th", { scope: "col" }, "Client"),
          COLS.map(([, t]) => el("th", { scope: "col" }, t)), el("th", { scope: "col" }, "Libellés"), el("th", { scope: "col", "data-tip": "Le Cpk exigé d'une caractéristique de chaque classe" }, "Cpk exigé"),
          el("th", { scope: "col" }, "Source"),
          el("th", { scope: "col" }, ""))), el("tbody", null, rows))),
      state.editable ? el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.101-class-customer", onclick: () => edit(state, null) }, "+ Ajouter un client") : null);
  }

  /* the dialog of one customer: name, the four symbols, the two labels, the source (its CSR) */
  function edit(state, c) {
    const fields = state.data.fields;
    const inputs = {};
    const box = el("div", { class: "dm-cls-form" }, Object.keys(fields).map((k) => {
      inputs[k] = el("input", { type: "text", value: c ? c[k] : "", maxlength: k === "source" ? 300 : k.endsWith("label") || k === "name" ? 80 : 12 });
      return DA.field(fields[k], inputs[k], k === "source" ? "Le document du client : CSR, manuel qualité, révision." : null);
    }), Object.keys(state.data.numbers || {}).map((k) => {  // 0.60.102 (D-O-110): the Cpk the customer requires
      inputs[k] = el("input", { type: "text", inputmode: "decimal", value: c ? cpk(c[k]) : k === "cc_cpk" ? "1,67" : "1,33", class: "dm-ch-short" });
      return DA.field(state.data.numbers[k], inputs[k], "Habituellement 1,67 pour une CC, 1,33 pour une SC");
    }));
    const err = el("p", { class: "dm-cls-err", role: "alert" });
    let close = () => {};
    const save = async () => {
      const body = {};
      Object.keys(inputs).forEach((k) => { body[k] = inputs[k].value; });
      try {
        state.data = await (c ? api.patch(state.base + "/customers/" + c.code, body) : api.post(state.base + "/customers", body));
        close();
        toast(c ? "Client modifié." : "Client ajouté au dictionnaire du Space.", "success");
        state.redraw();
      } catch (e) { err.textContent = e.message; }
    };
    box.append(err, el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn btn-primary", onclick: save }, "Enregistrer"),
      el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler")));
    close = DA.modal(c ? "Symboles de " + c.name : "Nouveau client", box);
    const dialogBox = box.closest(".modal");
    if (dialogBox) dialogBox.classList.add("dm-cls-modal");
  }

  A.views.dfmeaclass = view;
})();
