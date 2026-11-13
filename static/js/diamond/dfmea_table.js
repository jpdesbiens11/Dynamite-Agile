/* Diamond · DFMEA: the table (0.60.15). One row = one failure chain; the header of each column has the colour of its
   AIAG-VDA level -- Higher-Level Element white (where the effect lands), Focus Element blue (function, requirement,
   failure mode), Lower-Level Element orange (cause and controls: where the team works) -- and the two scores, RPN and AP.
   Cells save when they lose the focus; the row tools add below, duplicate, move up / down and delete; Alt + ↑ / ↓ moves
   the row from the keyboard. A value equal to the one above is shown faded, as the merged cells of a paper FMEA. */
(function () {
  "use strict";

  const { el } = DA;
  const COLS = [
    { key: "higher", label: "Higher-Level Element", group: "higher", type: "text", tip: "Utilisateur, produit ou système : là où l'effet arrive" },
    { key: "focus", label: "Focus Element", group: "focus", type: "text", tip: "Assemblage, sous-assemblage ou composant analysé" },
    { key: "lower", label: "Lower-Level Element", group: "lower", type: "text", tip: "Sous-composant, pièce ou caractéristique : là où naît la cause" },
    { key: "function_id", label: "Function of Focus Element", group: "focus", type: "function", tip: "Une fonction de l'arbre fonctionnel" },
    { key: "requirement", label: "Requirement / Characteristic", group: "focus", type: "area", tip: "Ce que la fonction doit tenir, mesurable" },
    { key: "failure_mode", label: "Failure Mode", group: "focus", type: "area", tip: "Comment la fonction peut ne pas être remplie" },
    { key: "effect", label: "Failure Effect", group: "higher", type: "area", tip: "La conséquence pour l'élément supérieur ou l'utilisateur" },
    { key: "severity", label: "S", group: "higher", type: "rating", tip: "Severity : gravité de l'effet, de 1 à 10" },
    // 0.61.0 (D-O-107): the class CC / SC, proposed by the rules of the Space, decided by a person (dfmea_class.js)
    { key: "class", label: "Class", group: "special", type: "class", fresh: "0.61.0-class-col", tip: "CC ou SC : proposée par la règle du Space (S, O), confirmée ou refusée par une personne" },
    { key: "class_decision", label: "Décision", group: "special", type: "decision", fresh: "0.61.0-class-decision-col", tip: "Qui a décidé la classe, quand et pourquoi ; un refus est gardé" },
    { key: "cause", label: "Failure Cause", group: "lower", type: "area", tip: "Pourquoi le mode de défaillance se produit" },
    { key: "prevention", label: "Prevention Controls", group: "lower", type: "area", tip: "Ce qui, en conception, empêche la cause" },
    { key: "occurrence", label: "O", group: "lower", type: "rating", tip: "Occurrence : probabilité de la cause, avec la prévention" },
    { key: "detection_ctrl", label: "Detection Controls", group: "lower", type: "area", tip: "Analyse ou essai qui trouve la cause ou le mode avant la production" },
    { key: "detection", label: "D", group: "lower", type: "rating", tip: "Detection : capacité du contrôle à trouver la défaillance (1 = toujours)" },
    { key: "rpn", label: "RPN", group: "score", type: "calc", tip: "S × O × D, de 1 à 1000" },
    { key: "ap", label: "AP", group: "score", type: "calc", tip: "Action Priority (AIAG-VDA) : High, Medium, Low" },
    { key: "action", label: "Actions", group: "lower", type: "area", tip: "Ce qui sera fait pour réduire O ou D (optimisation)" },
    // 0.60.38 (D-O-047): who carries the action, by when, where it stands, and its Agile ticket
    { key: "action_owner_id", label: "Responsable", group: "act", type: "owner", tip: "Le membre de l'équipe qui porte l'action" },
    { key: "action_due", label: "Échéance", group: "act", type: "date", tip: "La date où l'action doit être faite" },
    { key: "action_status", label: "Status", group: "act", type: "status", tip: "À faire, En cours, Fait — suit le ticket Agile s'il y en a un" },
    { key: "ticket", label: "Ticket Agile", group: "act", type: "ticket", tip: "« Suivre dans Agile » crée un ticket ; son status devient celui de la ligne" },
  ];

  function apBadge(ap, labels) {
    return el("span", { class: "dm-ap dm-ap-" + (ap || "none") }, ap ? labels[ap] : "—");
  }

  function cell(col, row, prev, state, save, editable, onKey) {
    const td = el("td", { class: "dm-fm-c dm-fm-" + col.group + " dm-fm-k-" + col.key });
    const same = prev && col.type !== "calc" && col.type !== "rating" && row[col.key] && prev[col.key] === row[col.key];
    if (same) td.classList.add("dm-fm-same");
    if (col.type === "calc") {
      td.append(col.key === "ap" ? apBadge(row.ap, state.data.labels.ap) : el("span", { class: "dm-fm-rpn" }, row.rpn ? String(row.rpn) : "—"));
      return td;
    }
    if (col.type === "class" || col.type === "decision") return DA.diamond.classCell(td, col, row, state, editable);  // 0.61.0
    if (col.key === "detection_ctrl") td.append(keyTest(row, state, save, editable));  // 0.60.24 (D-O-033)
    if (["owner", "date", "status", "ticket"].includes(col.type)) return actionCell(td, col, row, state, save, editable);
    if (!editable) {
      const text = col.type === "function" ? (row.function_number ? "F" + row.function_number + " " + row.function_text : "—") : (row[col.key] || "—");
      td.append(el("span", null, String(text)));
      return td;
    }
    let input;
    if (col.type === "rating") {
      input = el("select", { "aria-label": col.label + " ligne " + row.line }, [["", "—"]].concat([...Array(10)].map((_, i) => [i + 1, String(i + 1)]))
        .map(([v, label]) => el("option", { value: v, selected: String(row[col.key] || "") === String(v) }, label)));
    } else if (col.type === "function") {
      input = el("select", { "aria-label": "Fonction ligne " + row.line },
        [["", "— fonction de l'arbre —"]].concat(state.data.functions.map((f) => [f.id, "F" + f.number + " " + f.text]))
          .map(([v, label]) => el("option", { value: v, selected: String(row.function_id || "") === String(v) }, label)));
    } else if (col.type === "text") {
      input = el("input", { type: "text", value: row[col.key] || "", maxlength: 160, list: "dm-fm-list-" + col.key, "aria-label": col.label + " ligne " + row.line });
    } else {
      const lines = String(row[col.key] || "").split("\n").length;  // 0.60.28: the good practices, one per line
      input = el("textarea", { rows: Math.min(Math.max(lines, 2), 12), maxlength: { action: 600, prevention: 4000 }[col.key] || 400,
        "aria-label": col.label + " ligne " + row.line }, row[col.key] || "");
    }
    input.dataset.row = row.id;
    input.dataset.col = col.key;
    input.addEventListener("change", () => save(row.id, col.key, input.value));
    input.addEventListener("keydown", (ev) => onKey(ev, row, col));
    td.append(input);
    return td;
  }

  /* 0.60.24 (D-O-033): the key test of the Test Base that detects the failure -- one per row, chosen in a list (the Test
     Base of the Space, then the catalogue), changed or removed; the controls in words stay below it. */
  function keyTest(row, state, save, editable) {
    const name = (t) => t.code + " · " + t.title + (t.space && t.space !== state.key ? " (" + t.space + ")" : "");
    const link = row.test_code ? el("a", { class: "dm-fm-test-link", href: "#/testing/" + (row.test_space || state.key),
      "data-tip": "Ouvrir la Test Base de " + (row.test_space || state.key) }, editable ? "Ouvrir" : "🧪 " + row.test_code + " · " + row.test_title) : null;
    if (!editable) return el("div", { class: "dm-fm-test" }, link || el("span", { class: "muted" }, "Aucun essai clé"));
    const tests = state.data.tests || [];
    const pick = el("select", { class: "dm-fm-test-pick", "aria-label": "Essai clé ligne " + row.line, "data-new": "0.60.24-key-test" },
      el("option", { value: "" }, tests.length ? "— essai clé (Test Base) —" : "— aucun essai dans la Test Base —"),
      tests.map((t) => el("option", { value: t.id, selected: String(row.test_id || "") === String(t.id) }, name(t))));
    pick.dataset.row = row.id;
    pick.dataset.col = "test_id";
    pick.addEventListener("change", () => save(row.id, "test_id", pick.value ? Number(pick.value) : null));
    return el("div", { class: "dm-fm-test" }, pick, row.test_id ? el("button", { type: "button", class: "link-btn dm-fm-test-x",
      "aria-label": "Retirer l'essai clé de la ligne " + row.line, onclick: () => save(row.id, "test_id", null) }, "✕") : null, link);
  }

  /* 0.60.38 (D-O-047): the follow-up columns of the action */
  function actionCell(td, col, row, state, save, editable) {
    const tag = (n) => { n.dataset.row = row.id; n.dataset.col = col.key; return n; };
    const name = (state.data.members.find((m) => m.id === row.action_owner_id) || {}).display_name || row.action_owner_name || "";
    const statusLabel = state.data.labels.statuses[row.action_status] || row.action_status;
    if (row.late) td.classList.add("dm-fm-late");
    if (col.type === "ticket") {
      if (row.ticket) {
        td.append(el("a", { class: "dm-fm-ticket", href: row.ticket.href, "data-tip": row.ticket.status + (row.ticket.assignee ? " · " + row.ticket.assignee : "") },
          "🎫 " + row.ticket.key), el("span", { class: "muted dm-fm-ticket-st" }, row.ticket.status));
      } else if (editable && state.track) {
        td.append(el("button", { type: "button", class: "btn btn-small dm-fm-track", disabled: !String(row.action || "").trim(),
          "data-tip": String(row.action || "").trim() ? "Créer un ticket dans l'Agile de ce Space : le responsable, l'échéance, un lien vers cette ligne"
            : "Écrivez d'abord l'action", onclick: () => state.track(row.id) }, "Suivre dans Agile"));
      } else td.append(el("span", { class: "muted" }, "—"));
      return td;
    }
    if (!editable || (col.type === "status" && row.status_from_ticket)) {
      const text = col.type === "owner" ? name : col.type === "date" ? row.action_due : statusLabel;
      td.append(el("span", { class: col.type === "status" ? "dm-act-st dm-act-" + row.action_status : null,
        "data-tip": col.type === "status" && row.status_from_ticket ? "Suit le ticket " + row.ticket.key : null }, text || "—"));
      return td;
    }
    let input;
    if (col.type === "owner") {
      input = el("select", { "aria-label": "Responsable ligne " + row.line }, el("option", { value: "" }, "— personne —"),
        state.data.members.map((m) => el("option", { value: m.id, selected: m.id === row.action_owner_id }, m.display_name)));
    } else if (col.type === "date") {
      input = el("input", { type: "date", value: row.action_due || "", "aria-label": "Échéance ligne " + row.line });
    } else {
      input = el("select", { "aria-label": "Status de l'action ligne " + row.line, class: "dm-act-" + row.action_status },
        Object.entries(state.data.labels.statuses).map(([k, label]) => el("option", { value: k, selected: k === row.action_status }, label)));
    }
    tag(input).addEventListener("change", () => save(row.id, col.key, input.value));
    td.append(input);
    return td;
  }

  const completedText = (c) => [c.added + " ligne(s) ajoutée(s) (une par fonction sans ligne)", c.tested + " essai(s) clé(s) relié(s)",
    c.practices + " ligne(s) avec les bonnes pratiques"].join(" · ") + ".";

  /* opts: {state, visible: Set, editable, save(id, key, value), act(path, body), onKey} */
  function table(opts) {
    const { state, visible, editable } = opts;
    const cols = COLS.filter((c) => visible.has(c.key));
    const head = el("tr", null, el("th", { class: "dm-fm-tools-h", scope: "col" }, "#"),
      cols.map((c) => el("th", { scope: "col", class: "dm-fm-h dm-fm-h-" + c.group + (c.type === "rating" || c.type === "calc" ? " dm-fm-narrow" : ""),
        "data-tip": c.tip, "data-new": c.fresh || null }, c.label)));
    const rows = state.filtered;
    const body = el("tbody", null, rows.map((row, i) => {
      const prev = i > 0 ? rows[i - 1] : null;
      const tools = el("td", { class: "dm-fm-tools" }, el("span", { class: "dm-code" }, String(row.line)),
        editable ? el("span", { class: "dm-fm-btns" },
          el("button", { type: "button", class: "dm-fm-btn", "aria-label": "Monter la ligne " + row.line, "data-tip": "Monter (Alt + ↑)",
            disabled: row.line === 1, onclick: () => opts.act("/rows/" + row.id + "/move", { direction: "up" }) }, "↑"),
          el("button", { type: "button", class: "dm-fm-btn", "aria-label": "Descendre la ligne " + row.line, "data-tip": "Descendre (Alt + ↓)",
            disabled: row.line === state.data.rows.length, onclick: () => opts.act("/rows/" + row.id + "/move", { direction: "down" }) }, "↓"),
          el("button", { type: "button", class: "dm-fm-btn", "aria-label": "Ajouter une ligne sous la ligne " + row.line, "data-tip": "Ajouter une ligne dessous",
            onclick: () => opts.act("/rows", { after_id: row.id, higher: row.higher, focus: row.focus, function_id: row.function_id }) }, "+"),
          el("button", { type: "button", class: "dm-fm-btn", "aria-label": "Dupliquer la ligne " + row.line, "data-tip": "Dupliquer",
            onclick: () => opts.act("/rows/" + row.id + "/duplicate", {}) }, "⧉"),
          el("button", { type: "button", class: "dm-fm-btn dm-fm-del", "aria-label": "Effacer la ligne " + row.line, "data-tip": "Effacer",
            onclick: () => { if (window.confirm("Effacer la ligne " + row.line + " du DFMEA ? L'action est journalisée.")) opts.act("/rows/" + row.id + "/delete", {}); } }, "×"))
          : null);
      return el("tr", { class: "dm-fm-row dm-fm-ap-row-" + (row.ap || "none") + DA.diamond.classRow(row), "data-row": row.id }, tools,
        cols.map((c) => cell(c, row, prev, state, opts.save, editable, opts.onKey)));
    }));
    const lists = ["higher", "focus", "lower"].map((k) => el("datalist", { id: "dm-fm-list-" + k },
      (state.data.suggest[k] || []).map((v) => el("option", { value: v }))));
    return el("div", { class: "dm-scroll dm-fm-scroll" }, el("table", { class: "data dm-fm" }, el("thead", null, head), body), lists);
  }

  /* after a cell is saved: refresh the scores of its row without redrawing (the focus stays where it is); 0.61.0: and its class */
  function refreshRow(holder, row, labels, state) {
    const tr = holder.querySelector('tr[data-row="' + row.id + '"]');
    if (!tr) return;
    tr.className = "dm-fm-row dm-fm-ap-row-" + (row.ap || "none") + DA.diamond.classRow(row);
    if (state) {
      COLS.filter((c) => c.group === "special").forEach((c) => {
        const td = tr.querySelector(".dm-fm-k-" + c.key);
        if (td) td.replaceWith(DA.diamond.classCell(el("td", { class: "dm-fm-c dm-fm-special dm-fm-k-" + c.key }), c, row, state, state.editable));
      });
    }
    const rpn = tr.querySelector(".dm-fm-k-rpn"), ap = tr.querySelector(".dm-fm-k-ap");
    if (rpn) { while (rpn.firstChild) rpn.removeChild(rpn.firstChild); rpn.append(el("span", { class: "dm-fm-rpn" }, row.rpn ? String(row.rpn) : "—")); }
    if (ap) { while (ap.firstChild) ap.removeChild(ap.firstChild); ap.append(apBadge(row.ap, labels)); }
    const track = tr.querySelector(".dm-fm-track");  // 0.60.38: « Suivre dans Agile » once the action is written
    if (track) track.disabled = !String(row.action || "").trim();
  }

  DA.diamond = Object.assign(DA.diamond || {}, { DFMEA_COLS: COLS, dfmeaTable: table, dfmeaRefreshRow: refreshRow, apBadge, completedText });
})();
