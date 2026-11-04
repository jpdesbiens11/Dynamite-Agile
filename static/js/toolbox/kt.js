/* Tools - « Kepner-Tregoe » (D-B-067): decision analysis. DOIT criteria
   (pass / fail: an alternative that fails one is eliminated), VEUT criteria
   (weight 1-10, alternatives scored 1-10, weighted score), risks of the
   alternatives (probability x seriousness), decision with justification.
   Criteria can come from Goldmine needs / requirements. URL: #/tools/KEY/kt[/id]. */
(function () {
  "use strict";

  const { api, el, clear, field, toast, modal } = DA;
  const A = DA.agile;
  const base = (ctx) => "/api/tools/p/" + ctx.pid + "/kt";
  const LEVEL = { 1: "Faible", 2: "Moyenne", 3: "Élevée" };

  async function listView(page, ctx) {
    const data = await api.get(base(ctx));
    page.append(A.pageHead(ctx, [el("span", null, "Kepner-Tregoe")],
      A.canEdit(ctx) ? el("button", { type: "button", class: "btn btn-primary", onclick: () => openCreate(ctx) }, "Nouvelle analyse") : null));
    page.append(el("p", { class: "muted tl-intro" }, "Analyse de décision : DOIT éliminatoires, VEUT pondérés, puis risques des "
      + "meilleures alternatives. Les critères peuvent venir des needs et requirements Goldmine."));
    if (!data.analyses.length) { page.append(el("div", { class: "empty" }, el("p", null, "Aucune analyse dans ce Space."))); return; }
    page.append(DA.table(["Décision", "Alternatives", "Status", "Retenue", "Modifiée"], data.analyses.map((k) => el("tr", null,
      el("td", null, el("a", { href: A.href(ctx, "kt/" + k.id) }, k.title)), el("td", null, String(k.n_alts)),
      el("td", null, k.status === "decided" ? "Décidée" : "In Progress"), el("td", null, k.decision_name || "—"),
      el("td", { class: "muted nowrap" }, DA.formatDate(k.updated_at) + (k.updated_by_name ? " · " + k.updated_by_name : ""))))));
  }

  function openCreate(ctx) {
    const title = el("input", { type: "text", maxlength: 200, placeholder: "ex. Choisir le fournisseur de l'élément chauffant" });
    const statement = el("textarea", { rows: 2, maxlength: 1000, placeholder: "Choisir … pour …" });
    const alts = el("textarea", { rows: 3, placeholder: "Une alternative par ligne" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        const res = await api.post(base(ctx), { title: title.value, statement: statement.value,
          alternatives: alts.value.split("\n").map((x) => x.trim()).filter(Boolean) });
        close();
        location.hash = A.href(ctx, "kt/" + res.kt.id);
      } catch (err) { toast(err.message, "error"); }
    } }, field("Titre", title), field("Statement de la décision", statement), field("Alternatives", alts),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer")));
    close = modal("Nouvelle analyse Kepner-Tregoe", form);
    title.focus();
  }

  async function ktView(page, ctx) {
    const [data, gm] = await Promise.all([api.get(base(ctx) + "/" + ctx.arg),
      api.get("/api/agile/p/" + ctx.pid + "/goldmine").catch(() => ({ requirements: [] }))]);
    const state = { data, reqs: gm.requirements || [] };
    const holder = el("div");
    page.append(holder);
    draw(holder, ctx, state);
  }

  function draw(holder, ctx, state) {
    clear(holder);
    const { kt, criteria, alts, risks, results } = state.data;
    const editable = A.canEdit(ctx) && kt.status !== "decided";
    const scores = new Map(state.data.scores.map((s) => [s.criterion_id + ":" + s.alt_id, s]));
    const run = async (method, path, body) => {
      try { state.data = await api[method](base(ctx) + "/" + kt.id + path, body); } catch (err) { toast(err.message, "error"); }
      draw(holder, ctx, state);
    };
    holder.append(A.pageHead(ctx, [el("a", { href: A.href(ctx, "kt") }, "Kepner-Tregoe"), el("span", null, kt.title)], [
      A.canEdit(ctx) ? (kt.status === "decided"
        ? el("button", { type: "button", class: "btn", onclick: () => run("patch", "", { status: "draft" }) }, "Rouvrir")
        : el("button", { type: "button", class: "btn btn-primary", onclick: () => decide(ctx, state, run) }, "Décider")) : null]));
    if (kt.statement) holder.append(el("p", { class: "tl-prompt" }, kt.statement));
    if (kt.status === "decided") {
      const chosen = alts.find((a) => a.id === kt.decision_alt_id);
      holder.append(el("div", { class: "ag-import-advice ag-import-advice-ok" }, el("strong", null, "Décision : " + (chosen ? chosen.name : "?")),
        kt.decision_note ? el("p", null, kt.decision_note) : null));
    }
    if (editable) holder.append(toolbar(state, run));
    if (!alts.length || !criteria.length) {
      holder.append(el("div", { class: "empty" }, el("p", null, "Ajoutez des alternatives et des critères (DOIT et VEUT).")));
      if (!alts.length) return;
    }
    const cellFor = (c, a) => {
      const s = scores.get(c.id + ":" + a.id);
      const v = s ? s.value : "";
      if (!editable) {
        const txt = c.kind === "must" ? (v === 1 ? "Passe" : v === 0 ? "Échoue" : "·") : (v === "" ? "·" : v + " → " + v * c.weight);
        return el("td", { class: "kt-cell" + (c.kind === "must" && v === 0 ? " pg-minus" : "") }, txt);
      }
      const options = c.kind === "must" ? [["", "·"], ["1", "Passe"], ["0", "Échoue"]]
        : [["", "·"]].concat([...Array(10)].map((_, i) => [String(i + 1), String(i + 1)]));
      const sel = el("select", { "aria-label": c.text + " / " + a.name },
        options.map(([val, l]) => el("option", { value: val, selected: String(v) === val }, l)));
      sel.addEventListener("change", () => run("put", "/score", { criterion_id: c.id, alt_id: a.id, value: sel.value }));
      return el("td", { class: "kt-cell" + (c.kind === "must" && v === 0 ? " pg-minus" : c.kind === "must" && v === 1 ? " pg-plus" : "") },
        sel, c.kind === "want" && v !== "" ? el("span", { class: "kt-weighted" }, "= " + v * c.weight) : null);
    };
    const critCell = (c) => el("th", { scope: "row", class: "pg-crit" },
      c.issue_key ? el("a", { class: "ag-key", href: "#/goldmine/" + ctx.key + "/issue/" + c.issue_number }, c.issue_key) : null,
      c.issue_key ? " " : null, c.text,
      editable ? el("button", { type: "button", class: "icon-btn", "aria-label": "Retirer", title: "Retirer ce critère",
        onclick: () => run("patch", "/criteria/" + c.id, { delete: true }) }, "×") : null);
    const weightCell = (c) => {
      if (c.kind !== "want") return el("td", { class: "muted" }, "—");
      if (!editable) return el("td", { class: "pg-num" }, String(c.weight));
      const w = el("select", { "aria-label": "Poids" }, [...Array(10)].map((_, i) => el("option", { value: i + 1, selected: c.weight === i + 1 }, String(i + 1))));
      w.addEventListener("change", () => run("patch", "/criteria/" + c.id, { text: c.text, weight: Number(w.value) }));
      return el("td", null, w);
    };
    const section = (kind, label) => {
      const rows = criteria.filter((c) => c.kind === kind);
      return [el("tr", { class: "kt-section" }, el("th", { colspan: 2 + alts.length }, label + " (" + rows.length + ")"))]
        .concat(rows.map((c) => el("tr", null, critCell(c), weightCell(c), alts.map((a) => cellFor(c, a)))));
    };
    const r = (a) => results[a.id];
    const foot = [
      ["DOIT", (a) => r(a).eliminated ? el("strong", { class: "kt-out" }, "Éliminée") : r(a).pending_musts.length ? "à compléter" : "OK"],
      ["Score pondéré", (a) => r(a).eliminated ? "—" : r(a).weighted + " / " + r(a).max],
      ["% du maximum", (a) => r(a).eliminated ? "—" : r(a).percent + " %"],
      ["Rang", (a) => r(a).rank || "—"],
      ["Risque (Σ P × G)", (a) => String(r(a).risk)],
    ].map(([label, fn]) => el("tr", { class: "pg-total" }, el("th", { scope: "row", colspan: 2 }, label),
      alts.map((a) => el("td", { class: "pg-num" + (label === "Rang" && r(a).rank === 1 ? " pg-best" : "") }, fn(a)))));
    holder.append(el("div", { class: "pg-wrap" }, el("table", { class: "data pg-matrix" },
      el("thead", null, el("tr", null, el("th", null, "Critère"), el("th", null, "Poids"),
        alts.map((a) => el("th", { class: "pg-concept" }, el("span", { class: "pg-concept-name", title: a.description || "" }, a.name),
          editable ? el("button", { type: "button", class: "link-btn pg-concept-edit", onclick: () => {
            if (window.confirm("Retirer l'alternative « " + a.name + " » ?")) run("patch", "/alts/" + a.id, { delete: true });
          } }, "retirer") : null)))),
      el("tbody", null, section("must", "DOIT — éliminatoires"), section("want", "VEUT — pondérés (1 à 10)")),
      el("tfoot", null, foot))));
    holder.append(risksBlock(state, run, editable));
  }

  function toolbar(state, run) {
    const kind = el("select", { "aria-label": "Type" }, el("option", { value: "want" }, "VEUT"), el("option", { value: "must" }, "DOIT"));
    const text = el("input", { type: "text", maxlength: 300, placeholder: "Critère (ou choisir dans Goldmine)" });
    const weight = el("select", { "aria-label": "Poids" }, [...Array(10)].map((_, i) => el("option", { value: i + 1, selected: i === 4 }, "poids " + (i + 1))));
    const req = el("select", { "aria-label": "Need ou requirement Goldmine" }, el("option", { value: "" }, "— depuis Goldmine —"),
      state.reqs.filter((r) => !["Rejected", "Obsolete"].includes(r.status_name)).map((r) => el("option", { value: r.number },
        (r.kind === "need" ? "[Need] " : "") + r.key + " · " + r.title)));
    const alt = el("input", { type: "text", maxlength: 120, placeholder: "Nom de l'alternative" });
    return el("div", { class: "pg-toolbar" },
      el("div", { class: "pg-tool" }, el("strong", null, "Critères"), kind, text, req, weight,
        el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => {
          if (!text.value.trim() && !req.value) { text.focus(); return; }
          run("post", "/criteria", { kind: kind.value, text: text.value, weight: Number(weight.value), issue_number: req.value ? Number(req.value) : null });
        } }, "Ajouter")),
      el("div", { class: "pg-tool" }, el("strong", null, "Alternatives"), alt,
        el("button", { type: "button", class: "btn btn-small", onclick: () => {
          if (!alt.value.trim()) { alt.focus(); return; }
          run("post", "/alts", { name: alt.value });
        } }, "Ajouter")));
  }

  function risksBlock(state, run, editable) {
    const { alts, risks } = state.data;
    const box = el("section", { class: "kt-risks" }, el("h2", null, "Risques (conséquences négatives)"),
      el("p", { class: "muted" }, "Pour les meilleures alternatives : ce qui pourrait mal tourner si on la choisit. Probabilité × gravité "
        + "(1 Faible, 2 Moyenne, 3 Élevée)."));
    box.append(DA.table(["Alternative", "Risque", "Probabilité", "Gravité", "P × G", ""], risks.map((k) => el("tr", null,
      el("td", null, (alts.find((a) => a.id === k.alt_id) || {}).name || "?"), el("td", null, k.text),
      el("td", null, LEVEL[k.probability]), el("td", null, LEVEL[k.seriousness]), el("td", { class: "pg-num" }, String(k.probability * k.seriousness)),
      el("td", null, editable ? el("button", { type: "button", class: "icon-btn", "aria-label": "Retirer",
        onclick: () => run("patch", "/risks/" + k.id, { delete: true }) }, "×") : null)))));
    if (editable && alts.length) {
      const alt = el("select", { "aria-label": "Alternative" }, alts.map((a) => el("option", { value: a.id }, a.name)));
      const text = el("input", { type: "text", maxlength: 500, placeholder: "ex. Fournisseur unique : rupture d'approvisionnement" });
      const lvl = (label) => el("select", { "aria-label": label }, Object.entries(LEVEL).map(([v, l]) => el("option", { value: v }, label + " " + l)));
      const p = lvl("P :"), g = lvl("G :");
      box.append(el("div", { class: "pg-tool tl-risk-add" }, alt, text, p, g,
        el("button", { type: "button", class: "btn btn-small", onclick: () => {
          if (!text.value.trim()) { text.focus(); return; }
          run("post", "/risks", { alt_id: Number(alt.value), text: text.value, probability: Number(p.value), seriousness: Number(g.value) });
        } }, "Ajouter le risque")));
    }
    return box;
  }

  function decide(ctx, state, run) {
    const { alts, results } = state.data;
    const ranked = alts.slice().sort((a, b) => (results[a.id].rank || 99) - (results[b.id].rank || 99));
    const chosen = el("select", null, ranked.map((a) => el("option", { value: a.id }, a.name + (results[a.id].eliminated ? " — éliminée"
      : " — " + results[a.id].weighted + " pts, risque " + results[a.id].risk))));
    const note = el("textarea", { rows: 4, maxlength: 4000, placeholder: "Pourquoi : score, risques acceptés, actions de maîtrise" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: (ev) => {
      ev.preventDefault(); close();
      run("patch", "", { status: "decided", decision_alt_id: Number(chosen.value), decision_note: note.value });
    } }, field("Alternative retenue", chosen), field("Rationale", note),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Décider")));
    close = modal("Décider", form);
  }

  A.views.kt = (page, ctx) => (ctx.arg ? ktView(page, ctx) : listView(page, ctx));
})();
