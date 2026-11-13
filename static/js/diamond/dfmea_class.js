/* Diamond · DFMEA: the classes CC / SC (0.60.101, D-O-108). The platform proposes a class from S and O and the rules of
   the Space (classes.py), a person decides: « Class » shows the symbol of the Space's customer (red for CC, orange for SC,
   dashed while only proposed), « Décision » who decided, when and why -- a refusal is kept. The decision is taken in a
   dialog that asks for the reason and shows the earlier decisions of the row. The filters of the DFMEA: every row, CC ·
   SC, S >= the CC threshold, CC proposed, a confirmed class without its Requirement / Characteristic. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const D = DA.diamond;
  const day = (iso) => {  // « 20 oct. 2026 », or « Oct 20, 2026 » when the page is shown in English (i18n_dom.js)
    const d = new Date(iso);
    const lang = document.documentElement.lang === "en" ? "en-CA" : "fr-CA";
    return isNaN(d.getTime()) ? "" : d.toLocaleDateString(lang, { day: "numeric", month: "short", year: "numeric" });
  };

  function cls(data) { return (data && data.classes) || { rules: { cc_severity: 9, sc_severity: 5, sc_occurrence: 4 }, customer: {}, counts: {}, names: {} }; }
  const sym = (C, code) => (code && C.customer[code.toLowerCase() + "_dfmea"]) || code || "";
  const label = (C, code) => (code && C.customer[code.toLowerCase() + "_label"]) || (C.names || {})[code] || code;

  /* the chip of the « Class » column */
  function chip(row, data) {
    const C = cls(data), st = row.class_status, code = row.class_shown;
    if (st === "confirmed") {
      return el("span", { class: "dm-cls dm-cls-" + code, "data-tip": label(C, code) + " — confirmée" },
        code === "CC" && !/[∇▼]/.test(sym(C, code)) ? el("span", { class: "dm-cls-mark", "aria-hidden": "true" }, "▼") : null, sym(C, code));
    }
    if (st === "proposed") {
      return el("span", { class: "dm-cls dm-cls-prop dm-cls-" + code, "data-tip": label(C, code) + " — proposée par la règle, à décider" }, sym(C, code) + " ?");
    }
    if (st === "refused") return el("span", { class: "dm-cls dm-cls-off", "data-tip": label(C, code) + " — refusée" }, el("s", null, sym(C, code)));
    return el("span", { class: "dm-cls dm-cls-none" }, "aucune");
  }

  /* why the rule proposes (or not) */
  function ruleText(row, data) {
    const r = cls(data).rules;
    if (!row.severity) return "S non cotée : aucune proposition";
    if (row.class_proposed === "CC") return "Proposée : S " + row.severity + " ≥ " + r.cc_severity;
    if (row.class_proposed === "SC") return "Proposée : S " + row.severity + " (" + r.sc_severity + " à " + (r.cc_severity - 1) + ") et O " + row.occurrence + " ≥ " + r.sc_occurrence;
    return "S " + row.severity + " · O " + (row.occurrence || "—") + " : sous les seuils";
  }

  /* « Confirmée par LEX · 20 oct. 2026 · « reason » »: one text node per piece, so that the display dictionary translates
     each one (the reason of the demo too); the quotes of <q> follow the language of the page */
  function decisionText(row, data, prefix) {
    const C = cls(data);
    if (!row.class_state) return null;
    const who = row.class_by_initials || row.class_by_name || "?";
    const head = row.class_state === "confirmed" ? [el("span", null, "Confirmée")] : [sym(C, row.class_code) + " ", el("span", null, "refusée")];
    return el("p", { class: "dm-cls-who dm-cls-" + row.class_state }, prefix ? el("span", null, prefix) : null, prefix ? " " : null, head,
      " ", el("span", null, "par"), " " + who + " · " + day(row.class_at) + " · ", el("q", null, row.class_reason));  // « » or “ ” by the page's language
  }

  /* the cells « Class » and « Décision » */
  function cell(td, col, row, state, editable) {
    td.classList.add("dm-fm-special");
    if (col.type === "class") { td.append(chip(row, state.data)); return td; }
    const box = el("div", { class: "dm-cls-dec" });
    const said = decisionText(row, state.data, "");
    if (editable) {
      const open = (choice) => dialog(row, state, choice);
      box.append(el("div", { class: "dm-actions dm-cls-btns" }, row.class_status === "proposed"
        ? [el("button", { type: "button", class: "btn btn-small btn-primary", "data-new": "0.60.101-class-confirm", onclick: () => open(row.class_proposed) },
          el("span", null, "Confirmer"), " " + sym(cls(state.data), row.class_proposed)),
        el("button", { type: "button", class: "btn btn-small", onclick: () => open("refused") }, "Refuser")]
        : el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.101-class-review", onclick: () => open(row.class_state === "confirmed" ? row.class_code : "") },
          row.class_state ? "Revoir…" : "Classer…")));
    }
    if (said) box.append(said);
    if (row.class_status === "proposed" || !row.class_state) box.append(el("p", { class: "dm-cls-who" }, ruleText(row, state.data)));
    if (row.class_changed) {
      box.append(el("p", { class: "dm-cls-who dm-cls-changed" }, "Décidée sur S " + (row.class_severity || "—") + " · O " + (row.class_occurrence || "—")
        + " ; maintenant S " + (row.severity || "—") + " · O " + (row.occurrence || "—")));
    }
    td.append(box);
    return td;
  }

  /* the dialog of the decision: choice, reason (required), earlier decisions */
  function dialog(row, state, choice) {
    const C = cls(state.data);
    // [value, verb, symbol, meaning]: each piece its own text node (display dictionary)
    const options = [["CC", "Confirmer", sym(C, "CC"), label(C, "CC"), "sécurité ou loi"],
      ["SC", "Confirmer", sym(C, "SC"), label(C, "SC"), "ajustement, fonction, performance, satisfaction du client"]];
    const refusable = row.class_proposed || (row.class_state === "confirmed" ? row.class_code : "");
    if (refusable) options.push(["refused", "Refuser", sym(C, refusable), "", "la question est posée, la réponse est non (le refus est gardé)"]);
    if (row.class_state) options.push(["clear", "Retirer la décision", "", "", "revenir à la proposition de la règle"]);
    const pick = choice || row.class_proposed || "CC";
    const radios = options.map(([value, verb, code, name, text]) => {
      const input = el("input", { type: "radio", name: "dm-cls-choice", value, checked: value === pick });
      return el("label", { class: "dm-check dm-cls-opt" }, input, el("span", null, el("strong", null, el("span", null, verb), code ? " " + code : null), " — ",
        name ? el("span", null, name) : null, name ? " : " : null, el("span", null, text)));
    });
    const reason = el("textarea", { rows: 3, maxlength: 400, required: true, "aria-label": "Justification de la décision",
      placeholder: "Pourquoi ? ex. « peut blesser une personne », « fonction de vitesse », « cause logicielle, rien à contrôler en fabrication »" });
    const history = el("div", { class: "dm-cls-history" });
    const err = el("p", { class: "dm-cls-err", role: "alert" });
    let close = () => {};
    const save = async () => {
      const decision = (radios.map((l) => l.querySelector("input")).find((i) => i.checked) || {}).value;
      try {
        const res = await api.post(D.base(state.ctx) + "/dfmea/rows/" + row.id + "/class", { decision, reason: reason.value });
        state.data = res;
        close();
        toast("Décision tracée : ligne " + row.line + ".", "success");
        state.redraw();
      } catch (e) { err.textContent = e.message; }
    };
    const content = el("div", { class: "dm-cls-dialog" },
      el("p", null, el("strong", null, (row.function_number ? "F" + row.function_number + " " + row.function_text : "Sans fonction") + " — "),
        (row.failure_mode || "—") + " → " + (row.effect || "—") + " · S " + (row.severity || "—") + " · O " + (row.occurrence || "—")),
      el("p", { class: "muted" }, ruleText(row, state.data) + (C.customer.name ? " · symboles : " + C.customer.name : "")),
      decisionText(row, state.data, "Aujourd'hui :"),
      el("fieldset", { class: "dm-cls-choices" }, el("legend", null, "Décision"), radios),
      DA.field("Justification (obligatoire)", reason, "Elle est gardée avec votre nom et la date, comme chaque décision précédente."),
      err, el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn btn-primary", onclick: save }, "Enregistrer la décision"),
        el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler")), history);
    close = DA.modal("Classe de la ligne " + row.line, content);
    const box = content.closest(".modal");
    if (box) box.classList.add("dm-cls-modal");  // wider than the default dialog (480 px)
    if (row.class_history) loadHistory(history, row, state);
  }

  async function loadHistory(box, row, state) {
    try {
      const res = await api.get(D.base(state.ctx) + "/dfmea/rows/" + row.id + "/class");
      const C = cls(state.data);
      const what = (h) => (h.state === "cleared" ? "Décision retirée" : h.state === "refused" ? sym(C, h.class_code) + " refusée" : sym(C, h.class_code) + " confirmée");
      clear(box);
      box.append(el("details", null, el("summary", null, "Décisions précédentes (" + res.history.length + ")"),
        el("ul", null, res.history.map((h) => el("li", null, what(h) + " par " + (h.by_initials || h.by_name || "?") + " · " + day(h.decided_at)
          + " · S " + (h.severity || "—") + " · O " + (h.occurrence || "—") + " · « " + h.reason + " »")))));
    } catch (e) { /* the history is a help, the decision works without it */ }
  }

  const FILTERS = [["", "Toutes", "all"], ["special", "CC · SC", "special"], ["severe", "S ≥ #", "severe"], ["cc_proposed", "CC proposées", "cc_proposed"],
    ["no_characteristic", "SC sans caractéristique", "no_characteristic"]];
  const TIPS = { special: "Les lignes dont la classe CC ou SC est confirmée", severe: "Sévérité de sécurité ou de loi",
    cc_proposed: "Les CC que la règle propose et que personne n'a encore décidées",
    no_characteristic: "Classe CC ou SC confirmée dont la Requirement / Characteristic est vide : aucune caractéristique à tenir" };

  function keep(row, key, data) {
    if (!key) return true;
    if (key === "special") return row.special;
    if (key === "severe") return (row.severity || 0) >= cls(data).rules.cc_severity;
    if (key === "cc_proposed") return row.class_status === "proposed" && row.class_proposed === "CC";
    if (key === "no_characteristic") return row.special && !String(row.requirement || "").trim();
    return true;
  }

  function filters(state) {
    const C = cls(state.data), n = C.counts || {};
    return el("div", { class: "dm-fm-filters", role: "group", "aria-label": "Filtres des classes", "data-new": "0.60.101-class-filters" },
      el("span", { class: "dm-fm-filters-h" }, "Filtres"),
      FILTERS.map(([key, text, count]) => el("button", { type: "button", class: "btn btn-small", "aria-pressed": String((state.cls || "") === key),
        "data-tip": TIPS[key] || null, onclick: () => { state.cls = key; state.redraw(); } },
      text.replace("#", C.rules.cc_severity), el("span", { class: "dm-fm-count" }, String(n[count] || 0)))));
  }

  function refreshFilters(holder, state) {
    const old = holder.querySelector(".dm-fm-filters");
    if (old) old.replaceWith(filters(state));
  }

  const rowClass = (row) => (row.class_status === "confirmed" ? " dm-fm-cls-" + row.class_code : row.class_status === "proposed" ? " dm-fm-cls-prop-" + row.class_proposed : "");

  DA.diamond = Object.assign(DA.diamond || {}, { classCell: cell, classChip: chip, classKeep: keep, classFilters: filters,
    classRefreshFilters: refreshFilters, classRow: rowClass });
})();
