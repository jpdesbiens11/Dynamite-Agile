/* Agile - Change Management block on the ticket page (D-B-010, D-B-011).
   PR / bug: problem fields, ECN treating it, « Dériver en ECN ».
   ECN: change fields (class, reason, impacts, effectivity, CCB), the items it
   changes (part / assembly / drawing / document / software, revision from ->
   to, stock disposition) and the problems it treats. Each status shows what
   the next step needs, the same rules the server enforces. */
(function () {
  "use strict";

  const { api, el, clear, field, toast } = DA;
  const A = DA.agile;

  const NEXT_STEP = {
    "Open": "Passez à « In Analysis » pour analyser le problème.",
    "In Analysis": "Dérivez en ECN (bouton ci-dessous), ou fermez avec la cause racine, ou rejetez.",
    "Derived to ECN": "Se ferme quand tous les ECN qui le traitent sont fermés.",
    "Draft": "Pour soumettre au CCB : classe, raison, description du changement et au moins un article.",
    "Submitted": "Le CCB met l'ECN en revue.",
    "CCB Review": "Décision CCB (administrateur du projet) : nommez les approbateurs avant d'approuver.",
    "Approved": "Découpez le travail en sub-tasks, puis démarrez l'implantation.",
    "In Implementation": "Toutes les sub-tasks doivent être terminées avant la vérification.",
    "In Verification": "Pour fermer : effectivité et référence de vérification de l'implantation.",
  };

  function base(ctx) { return "/api/agile/p/" + ctx.pid; }
  function issueUrl(ctx, issue) { return base(ctx) + "/issues/" + issue.number; }

  function linkedList(title, list, empty) {
    return el("div", { class: "gm-linked" }, el("h3", null, title),
      list && list.length ? el("ul", { class: "ag-rows" }, list.map((t) => el("li", { class: "ag-row" },
        el("a", { class: "ag-key", href: "#/agile/" + t.project_key + "/issue/" + t.number }, t.key),
        el("span", { class: "ag-row-title" }, t.title), A.statusBadge(t.status_name, t.status_category))))
        : el("p", { class: "muted" }, empty));
  }

  /* Field form; `names` from the server's list, labels from change_labels. */
  function fieldsForm(ctx, issue, names, editable, reload) {
    const L = issue.change_labels;
    const v = issue.change;
    const choices = { severity: L.severities, detected_in: L.detected_in, change_class: L.classes, reason: L.reasons };
    const long = ["containment", "root_cause", "impact_notes"];
    const inputs = {};
    const impacts = el("div", { class: "gm-impacts" }, el("span", { class: "gm-impacts-title" }, "Impacts"));
    const rows = names.map((name) => {
      let input;
      if (choices[name]) input = el("select", { disabled: !editable }, A.options(Object.entries(choices[name]), v[name] || "", "—"));
      else if (name.startsWith("impact_") && name !== "impact_notes") {
        input = el("input", { type: "checkbox", checked: !!v[name], disabled: !editable });
        inputs[name] = input;
        impacts.append(el("label", { class: "check" }, input, L.fields[name].replace(/^Impact /, "")));
        return impacts.childNodes.length === 2 ? impacts : null;
      } else if (long.includes(name)) { input = el("textarea", { rows: 3, maxlength: 4000, disabled: !editable }); input.value = v[name] || ""; }
      else if (name === "decision_date") input = el("input", { type: "date", value: v[name] || "", disabled: !editable });
      else input = el("input", { type: "text", value: v[name] || "", maxlength: 300, disabled: !editable });
      inputs[name] = input;
      const f = field(L.fields[name], input);
      if (long.includes(name)) f.classList.add("gm-wide");
      return f;
    });
    const save = el("button", { type: "button", class: "btn btn-primary btn-small", onclick: async () => {
      const body = {};
      names.forEach((n) => { body[n] = inputs[n].type === "checkbox" ? inputs[n].checked : inputs[n].value; });
      save.disabled = true;
      try {
        const res = await api.put(issueUrl(ctx, issue) + "/change", body);
        toast(res.changed.length ? "Fiche enregistrée." : "Aucun changement.", "success");
        reload();
      } catch (err) { toast(err.message, "error"); save.disabled = false; }
    } }, "Enregistrer la fiche");
    return el("div", null, el("div", { class: "gm-grid" }, rows.filter(Boolean)), editable ? el("div", { class: "form-actions" }, save) : null);
  }

  function itemsEditor(ctx, issue, editable, reload) {
    const L = issue.change_labels;
    let items = (issue.change_items || []).map((it) => Object.assign({}, it));
    const body = el("tbody");
    const blank = () => ({ item_type: "piece", item_number: "", item_title: "", rev_from: "", rev_to: "", disposition: "na" });
    function draw() {
      clear(body);
      if (!items.length) body.append(el("tr", null, el("td", { colspan: 7, class: "muted" }, "Aucun article : ajoutez chaque pièce, assemblage, plan, document ou logiciel touché.")));
      items.forEach((it, i) => {
        const cell = (name, attrs) => {
          const input = el("input", Object.assign({ type: "text", value: it[name] || "", disabled: !editable,
            "aria-label": name }, attrs));
          input.addEventListener("input", () => { it[name] = input.value; });
          return el("td", null, input);
        };
        const pick = (name, map) => {
          const s = el("select", { disabled: !editable, "aria-label": name }, A.options(Object.entries(map), it[name]));
          s.addEventListener("change", () => { it[name] = s.value; });
          return el("td", null, s);
        };
        body.append(el("tr", null, pick("item_type", L.item_types),
          cell("item_number", { maxlength: 60, placeholder: "DWG-46000-12345", class: "gm-mono" }),
          cell("item_title", { maxlength: 200, placeholder: "Désignation" }),
          cell("rev_from", { maxlength: 10, placeholder: "B", class: "gm-rev" }),
          cell("rev_to", { maxlength: 10, placeholder: "C", class: "gm-rev" }),
          pick("disposition", L.dispositions),
          el("td", null, editable ? el("button", { type: "button", class: "icon-btn", "aria-label": "Retirer l'article",
            onclick: () => { items.splice(i, 1); draw(); } }, "×") : null)));
      });
    }
    draw();
    const table = el("table", { class: "data gm-items" },
      el("thead", null, el("tr", null, ["Type", "Numéro", "Désignation", "Rév. actuelle", "Nouvelle rév.", "Disposition du stock", ""]
        .map((h) => el("th", null, h)))), body);
    const actions = editable ? el("div", { class: "form-actions gm-items-actions" },
      el("button", { type: "button", class: "btn btn-small", onclick: () => { items.push(blank()); draw(); } }, "+ Ajouter un article"),
      el("button", { type: "button", class: "btn btn-primary btn-small", onclick: async () => {
        try {
          const res = await api.put(issueUrl(ctx, issue) + "/change/items", { items });
          toast(res.changed ? "Articles enregistrés." : "Aucun changement.", "success");
          reload();
        } catch (err) { toast(err.message, "error"); }
      } }, "Enregistrer les articles")) : null;
    return el("div", { class: "gm-items-wrap" }, el("h3", null, "Articles touchés"), el("div", { class: "table-wrap" }, table), actions);
  }

  function changeBlock(ctx, issue, editable, reload) {
    const role = issue.change_role;
    if (!issue.change) return null;  // ECN sub-task: plain ticket
    const next = NEXT_STEP[issue.status_name];
    const box = el("section", { class: "ag-block gm-change", "aria-label": "Gestion du changement" },
      el("div", { class: "ag-block-head" }, el("h2", null, role === "ecn" ? "Gestion du changement (ECN)"
        : (role === "bug" ? "Bug logiciel" : "Rapport de problème (PR)"))),
      next ? el("p", { class: "gm-next" }, "Étape suivante : " + next) : null);
    if (role === "ecn") {
      box.append(fieldsForm(ctx, issue, ["change_class", "reason", "impact_fff", "impact_certification", "impact_safety",
        "impact_notes", "effectivity", "approvers", "decision_date", "verification_ref"], editable, reload),
      itemsEditor(ctx, issue, editable, reload),
      linkedList("Problèmes traités", issue.treats, "Aucun PR ni bug lié (changement non correctif)."));
      return box;
    }
    const names = ["severity", "detected_in", "item_ref"].concat(role === "bug" ? ["found_version"] : [], ["containment", "root_cause"]);
    box.append(fieldsForm(ctx, issue, names, editable, reload),
      linkedList("Handled By", issue.treated_by, "Aucun ECN pour l'instant."));
    if (editable) {
      const canDerive = ["In Analysis", "Derived to ECN"].includes(issue.status_name);
      box.append(el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn btn-primary",
        disabled: !canDerive, title: canDerive ? "" : "Passez d'abord le problème à « In Analysis »",
        onclick: async () => {
          try {
            const made = await api.post(issueUrl(ctx, issue) + "/derive", {});
            toast(made.key + " créé et lié à " + issue.key + ".", "success");
            location.hash = "#/agile/" + ctx.key + "/issue/" + made.number;
          } catch (err) { toast(err.message, "error"); }
        } }, issue.treated_by && issue.treated_by.length ? "Dériver un autre ECN" : "Dériver en ECN")));
    }
    return box;
  }

  A.changeBlock = changeBlock;
})();
