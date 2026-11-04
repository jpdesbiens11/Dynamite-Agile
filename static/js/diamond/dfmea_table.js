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
    { key: "cause", label: "Failure Cause", group: "lower", type: "area", tip: "Pourquoi le mode de défaillance se produit" },
    { key: "prevention", label: "Prevention Controls", group: "lower", type: "area", tip: "Ce qui, en conception, empêche la cause" },
    { key: "occurrence", label: "O", group: "lower", type: "rating", tip: "Occurrence : probabilité de la cause, avec la prévention" },
    { key: "detection_ctrl", label: "Detection Controls", group: "lower", type: "area", tip: "Analyse ou essai qui trouve la cause ou le mode avant la production" },
    { key: "detection", label: "D", group: "lower", type: "rating", tip: "Detection : capacité du contrôle à trouver la défaillance (1 = toujours)" },
    { key: "rpn", label: "RPN", group: "score", type: "calc", tip: "S × O × D, de 1 à 1000" },
    { key: "ap", label: "AP", group: "score", type: "calc", tip: "Action Priority (AIAG-VDA) : High, Medium, Low" },
    { key: "action", label: "Actions", group: "lower", type: "area", tip: "Ce qui sera fait pour réduire O ou D (optimisation)" },
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
    if (col.key === "detection_ctrl") td.append(keyTest(row, state, save, editable));  // 0.60.24 (D-O-033)
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
      input = el("textarea", { rows: 2, maxlength: col.key === "action" ? 600 : 400, "aria-label": col.label + " ligne " + row.line }, row[col.key] || "");
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

  /* opts: {state, visible: Set, editable, save(id, key, value), act(path, body), onKey} */
  function table(opts) {
    const { state, visible, editable } = opts;
    const cols = COLS.filter((c) => visible.has(c.key));
    const head = el("tr", null, el("th", { class: "dm-fm-tools-h", scope: "col" }, "#"),
      cols.map((c) => el("th", { scope: "col", class: "dm-fm-h dm-fm-h-" + c.group + (c.type === "rating" || c.type === "calc" ? " dm-fm-narrow" : ""),
        "data-tip": c.tip }, c.label)));
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
      return el("tr", { class: "dm-fm-row dm-fm-ap-row-" + (row.ap || "none"), "data-row": row.id }, tools,
        cols.map((c) => cell(c, row, prev, state, opts.save, editable, opts.onKey)));
    }));
    const lists = ["higher", "focus", "lower"].map((k) => el("datalist", { id: "dm-fm-list-" + k },
      (state.data.suggest[k] || []).map((v) => el("option", { value: v }))));
    return el("div", { class: "dm-scroll dm-fm-scroll" }, el("table", { class: "data dm-fm" }, el("thead", null, head), body), lists);
  }

  /* after a cell is saved: refresh the scores of its row without redrawing (the focus stays where it is) */
  function refreshRow(holder, row, labels) {
    const tr = holder.querySelector('tr[data-row="' + row.id + '"]');
    if (!tr) return;
    tr.className = "dm-fm-row dm-fm-ap-row-" + (row.ap || "none");
    const rpn = tr.querySelector(".dm-fm-k-rpn"), ap = tr.querySelector(".dm-fm-k-ap");
    if (rpn) { while (rpn.firstChild) rpn.removeChild(rpn.firstChild); rpn.append(el("span", { class: "dm-fm-rpn" }, row.rpn ? String(row.rpn) : "—")); }
    if (ap) { while (ap.firstChild) ap.removeChild(ap.firstChild); ap.append(apBadge(row.ap, labels)); }
  }

  DA.diamond = Object.assign(DA.diamond || {}, { DFMEA_COLS: COLS, dfmeaTable: table, dfmeaRefreshRow: refreshRow, apBadge });
})();
