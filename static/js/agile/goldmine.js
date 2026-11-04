/* Agile - Goldmine: engineering requirements (D-A-032). Matrix of the
   project's requirements, a panel of traceability gaps (what is missing,
   and how to fix it), a creation form, and the requirement block shown on
   a requirement's ticket page. */
(function () {
  "use strict";

  const { api, el, clear, field, toast, modal } = DA;
  const A = DA.agile;

  /* D-B-085: technical vocabulary in English (same labels as the server, modules/agile/goldmine.py) */
  const SOURCES = { client: "Customer", standard: "Standard", internal: "Internal", derived: "Derived" };
  const CATEGORIES = { functional: "Functional", performance: "Performance", interface: "Interface",
    environmental: "Environmental", safety: "Safety", personnel_safety: "Personnel Safety",
    regulatory: "Standard / Regulatory" };  // D-B-056
  /* D-B-055: phase of the life cycle -- its colour marks the row (gm-lc-<code>, themes in agile.css). */
  const LIFECYCLE = { design: "Design", cost: "Cost (DTC)", manufacturing: "Part Manufacturing (DFM)",
    assembly: "Assembly (DFA)", test: "Test & Verification (DFT)", transport: "Transport & Storage",
    installation: "Installation & Integration", operation: "Operation (Use)",
    maintenance: "Maintenance & Repair", appearance: "Appearance & Appeal", second_life: "Second Life",
    end_of_life: "End of Life (Disassembly, Recycling)" };
  const phaseChip = (code) => code
    ? el("span", { class: "gm-phase gm-lc-" + code }, LIFECYCLE[code] || code)
    : el("span", { class: "muted" }, "—");
  const METHODS = { I: "Inspection", A: "Analysis", D: "Demonstration", T: "Test" };
  /* D-B-064: stakeholder needs; a requirement names the needs it derives from */
  const KINDS = { requirement: "Requirement", need: "Need" };
  const STAKEHOLDERS = { client: "Customer / Buyer", user: "End User", authority: "Standards Body / Regulator",
    integrator: "Integrator / Distributor", production: "Production / Assemblers", repair: "Maintenance & Repair", logistics: "Logistics",
    recycling: "Recycling / End of Life", marketing: "Marketing / Sales", management: "Project Management",
    safety: "Health & Safety" };
  const GAPS = {
    no_implementation: ["acceptée(s) sans ticket d'implémentation",
      "Depuis un ticket de travail : Liens → « implémente (requirement) » → clé du requirement."],
    no_acceptance: ["acceptée(s) sans acceptance criteria",
      "Ouvrez le requirement et remplissez « Acceptance Criteria »."],
    no_verification_ref: ["en vérification sans référence de test",
      "Indiquez le test ou le rapport dans « Verification Ref. » : obligatoire pour passer à « Verified »."],
    no_need: ["sans besoin d'origine",
      "Indiquez dans « Derived From » l'ID du need (ex. GN-004) : chaque requirement répond à une stakeholder."],
    unknown_need: ["dérivée(s) d'un need introuvable",
      "Corrigez l'ID dans « Derived From », ou créez le need (Nature : Need)."],
    no_test: ["sans « Test Procedure »",
      "Ouvrez le requirement → Modifier → choisissez son test dans « Test Procedure » (base Testing) : obligatoire pour l'enregistrer."],
    no_method: ["ouverte(s) sans verification method",
      "Choisissez I, A, D ou T (plusieurs possibles) dans la fiche requirement."],
  };

  function base(ctx) { return "/api/agile/p/" + ctx.pid; }
  const FILTERS = {};  // D-B-069: filter values per Space, kept while the page is open
  /* [1,2,3,7,9,10] -> "1-3,7,9-10": the on-screen subset in a short URL */
  function ranges(numbers) {
    const sorted = numbers.slice().sort((a, b) => a - b);
    const out = [];
    sorted.forEach((n) => {
      const last = out[out.length - 1];
      if (last && n === last[1] + 1) last[1] = n; else out.push([n, n]);
    });
    return out.map(([a, b]) => (a === b ? String(a) : a + "-" + b)).join(",");
  }
  /* ISO UTC -> local aaaa-mm-jj, compared with the « depuis » date box */
  function localDay(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return "";
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }
  const methodText = (code) => (code || "").split("").map((c) => METHODS[c] || c).join(" + ");

  /* ---------- Shared field controls ---------- */
  function controls(values) {
    const v = values || {};
    const text = (name, max, placeholder) => el("input", { type: "text", maxlength: max, value: v[name] || "",
      placeholder: placeholder || "" });
    const area = (name, rows, max, placeholder) => {
      const t = el("textarea", { rows, maxlength: max, placeholder: placeholder || "" });
      t.value = v[name] || "";
      return t;
    };
    const select = (name, map, empty) => el("select", null,
      A.options(Object.entries(map), v[name] || "", empty));
    const methods = el("span", { class: "gm-methods" }, Object.entries(METHODS).map(([code, label]) =>
      el("label", { class: "check" }, el("input", { type: "checkbox", value: code,
        checked: (v.verification_method || "").includes(code) }), code + " · " + label)));
    const c = {
      external_id: text("external_id", 40, "ex. SYS-045"),
      kind: select("kind", KINDS),
      stakeholder: select("stakeholder", STAKEHOLDERS, "—"),
      derived_from: text("derived_from", 400, "ex. GN-004, GN-005"),
      source: select("source", SOURCES),
      source_doc: text("source_doc", 200, "ex. Spec client rév. B, §4.2.1"),
      statement: area("statement", 3, 4000, "Le système doit…"),
      rationale: area("rationale", 2, 4000, "Pourquoi ce requirement existe"),
      category: select("category", CATEGORIES),
      lifecycle: select("lifecycle", LIFECYCLE, "— non classée —"),
      criticality: select("criticality", { A: "A", B: "B", C: "C", D: "D", E: "E" }, "—"),
      methods,
      acceptance_criteria: area("acceptance_criteria", 2, 2000, "Mesurable : ex. surface accessible ≤ 45 °C après 30 min"),
      allocation: text("allocation", 120, "ex. Sous-système de chauffage"),
      verification_ref: text("verification_ref", 200, "ex. RVE-012 rév. A (test X)"),
      revision: text("revision", 10, "A"),
      received_at: el("input", { type: "date", value: v.received_at || "" }),
    };
    /* D-B-079: tests of the Testing base (mandatory for a requirement) */
    /* D-B-082: product functions F-XX (central list of Testing) */
    let fpicker = null;
    c.functionsBox = el("div", null, el("span", { class: "muted" }, "Chargement…"));
    c.test_ref = A.testPicker(v.test_ref, () => ({ category: c.category.value, lifecycle: c.lifecycle.value, kind: c.kind.value,
      functions: fpicker ? fpicker.value() : v.functions }));
    DA.gt.options().then((d) => {
      fpicker = DA.gt.chipPicker(d.functions, v.functions, { short: false, placeholder: "+ Ajouter une fonction…",
        empty: "Aucune fonction", label: "Ajouter une fonction", onchange: c.test_ref.refresh });
      clear(c.functionsBox);
      c.functionsBox.append(fpicker.node);
      c.test_ref.refresh();
    }).catch(() => { clear(c.functionsBox); });
    [c.kind, c.category, c.lifecycle].forEach((s) => s.addEventListener("change", c.test_ref.refresh));
    const need = A.needFields.controls(v, c.kind);  // D-B-086: Need Status
    c.values = () => Object.assign(need.values(), {
      external_id: c.external_id.value, kind: c.kind.value, stakeholder: c.stakeholder.value,
      derived_from: c.derived_from.value, source: c.source.value, source_doc: c.source_doc.value,
      statement: c.statement.value, rationale: c.rationale.value, category: c.category.value,
      lifecycle: c.lifecycle.value, criticality: c.criticality.value, acceptance_criteria: c.acceptance_criteria.value,
      allocation: c.allocation.value, verification_ref: c.verification_ref.value,
      revision: c.revision.value, received_at: c.received_at.value, test_ref: c.test_ref.value(),
      functions: fpicker ? fpicker.value() : (v.functions || ""),
      verification_method: Array.from(methods.querySelectorAll("input:checked")).map((i) => i.value).join(""),
    });
    c.layout = () => [
      el("div", { class: "form-row" }, field("Nature", c.kind), field("External ID", c.external_id), field("Revision", c.revision),
        field("Received", c.received_at)),
      el("div", { class: "form-row" }, field("Stakeholder", c.stakeholder),
        field("Derived From", c.derived_from, "ID ou clé des needs, séparés par des virgules")),
      ...need.layout(),
      field("Statement", c.statement, "Une seule requirement, vérifiable, au présent de l'obligation (« doit »)"),
      el("div", { class: "form-row" }, field("Source", c.source), field("Source Document", c.source_doc)),
      el("div", { class: "form-row" }, field("Category", c.category), field("Life-Cycle Phase", c.lifecycle),
        field("Criticality", c.criticality), field("Allocation", c.allocation)),
      el("div", { class: "field" }, el("span", { class: "field-label" }, "Functions (analyse fonctionnelle, F-XX)"), c.functionsBox),
      field("Verification Method (IADT)", c.methods),
      el("div", { class: "field gt-field" }, el("span", { class: "field-label" }, "Test Procedure (tests Testing) *"), c.test_ref.node),
      field("Acceptance Criteria", c.acceptance_criteria),
      field("Verification Ref.", c.verification_ref, "Test, analyse ou rapport qui prouve le requirement"),
      field("Rationale", c.rationale),
    ];
    return c;
  }

  function openCreate(ctx, reload) {
    const title = el("input", { type: "text", maxlength: 255, placeholder: "Titre court (sinon : début du Statement)" });
    const c = controls({ source: "client", category: "functional", revision: "A", kind: "requirement" });
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      error.textContent = "";
      try {
        const created = await api.post(base(ctx) + "/goldmine/requirements",
          Object.assign({ title: title.value }, c.values()));
        close();
        toast(created.key + " créée (status « Received »).", "success");
        reload();
      } catch (err) { error.textContent = err.message; }
    } }, field("Title", title), c.layout(), error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer le requirement")));
    close = modal("Nouveau Requirement", form);
    const dialogs = document.querySelectorAll(".modal");
    dialogs[dialogs.length - 1].classList.add("modal-wide");
    c.statement.focus();
  }

  /* D-B-064: « besoin → requirements » trace under the statement */
  function traceLine(ctx, r) {
    const keys = r.kind === "need" ? (r.derived_requirements || []) : (r.needs || []);
    const who = r.kind === "need" && r.stakeholder ? (STAKEHOLDERS[r.stakeholder] || r.stakeholder) + " · " : "";
    if (!keys.length && !who) return null;
    return el("div", { class: "gm-trace" }, who, keys.length ? (r.kind === "need" ? "Requirements : " : "Derived From : ") : "",
      keys.flatMap((k, i) => [i ? ", " : "", el("a", { class: "ag-key", href: A.href(ctx, "issue/" + k.split("-").pop()) }, k)]));
  }

  /* ---------- Goldmine screen ---------- */
  function gapsPanel(ctx, gaps) {
    const entries = Object.entries(GAPS).filter(([k]) => (gaps[k] || []).length);
    if (!entries.length) {
      return el("div", { class: "ag-import-advice ag-import-advice-ok" },
        el("strong", null, "Traçabilité complète : aucune requirement en défaut."));
    }
    return el("div", { class: "ag-import-advice gm-gaps" },
      el("strong", null, "À compléter pour la traçabilité"),
      el("ul", null, entries.map(([k, [label, fix]]) => el("li", null,
        el("span", { class: "gm-gap-count" }, String(gaps[k].length)), " requirement(s) " + label + " : ",
        gaps[k].flatMap((key, i) => [i ? ", " : "", el("a", { class: "ag-key",
          href: A.href(ctx, "issue/" + key.split("-").pop()) }, key)]),
        el("div", { class: "ag-import-fix" }, "→ " + fix)))));
  }

  async function goldmineView(page, ctx) {
    const data = await api.get(base(ctx) + "/goldmine");
    const reload = () => { clear(page); goldmineView(page, ctx); };
    page.append(A.pageHead(ctx, [el("span", null, "Requirements et needs")],
      data.enabled && A.canEdit(ctx) ? el("button", { type: "button", class: "btn",
        onclick: () => openCreate(ctx, reload) }, "Nouveau Requirement") : null));
    if (!data.enabled) {
      page.append(el("div", { class: "empty" },
        el("h2", null, "Goldmine n'est pas activé sur ce projet"),
        el("p", { class: "muted" }, "L'activation crée le type « Requirement » et son workflow : Reçue → En analyse "
          + "(↔ Clarification client) → Acceptée → Allouée → Implémentée → En vérification → Vérifiée "
          + "(ou Rejetée, Obsolète). Conseil : gardez les requirements dans un projet dédié et liez-y les "
          + "tickets de travail des autres projets."),
        A.isAdmin(ctx) ? el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
          try { await api.post(base(ctx) + "/goldmine/setup"); toast("Goldmine activé.", "success"); ctx.refresh(); }
          catch (err) { toast(err.message, "error"); }
        } }, "Activer Goldmine") : el("p", null, "Demandez à un administrateur de l'activer.")));
      return;
    }
    const reqs = data.requirements;
    /* D-B-069: the export follows the filters -- what is on screen is what goes to Excel */
    let shown = reqs;
    const exportBtn = el("button", { type: "button", class: "btn btn-small", onclick: () => {
      if (!shown.length) return;
      A.triggerDownload(ctx, "requirements", shown.length === reqs.length ? "" : "?numbers=" + ranges(shown.map((r) => r.number)));
    } });
    const exportAll = el("button", { type: "button", class: "link-btn", onclick: () => A.triggerDownload(ctx, "requirements") });
    /* D-B-083: the filtered list as a requirement specification (Word, Codebeamer-style items) */
    const wordBtn = el("button", { type: "button", class: "btn btn-small", onclick: () => {
      if (!shown.length) return;
      DA.gt.wordDialog("Exporter en Word — spécification de requirements", { title: ctx.key + " — Requirement Specification",
        doctype: "System Requirement Specification", note: shown.length + " élément(s) : ceux affichés avec les filtres actuels." },
      [["category", "Category"], ["function", "Function"], ["lifecycle", "Life-Cycle Phase"]], (params) => {
        if (shown.length !== reqs.length) params.set("numbers", ranges(shown.map((r) => r.number)));
        DA.gt.download(base(ctx) + "/export/requirements.docx?" + params.toString());
      });
    } }, "Exporter en Word (.docx)");
    page.append(el("div", { class: "ag-csv-toolbar" }, exportBtn, exportAll, wordBtn,
      A.canEdit(ctx) ? A.goldmineImportButton(ctx, "Importer une spec / des requirements (CSV)", reload) : null));
    if (!reqs.length && A.canEdit(ctx)) {  // D-B-134: a Space with no requirement yet
      page.append(DA.spaces.startHere("Les requirements de " + ctx.key + " commencent ici",
        "Chaque requirement suit son workflow (Reçue → … → Vérifiée) et nomme le test de Testing qui le vérifie. Écrivez le "
        + "premier, ou importez une spec client (CSV, revue avant écriture).",
        [["Nouveau Requirement", () => openCreate(ctx, reload), true]]));
    }
    page.append(gapsPanel(ctx, data.gaps));

    const q = el("input", { type: "search", placeholder: "Filtrer (ID, statement, allocation…)", "aria-label": "Filtrer" });
    const status = el("select", { "aria-label": "Status" },
      A.options(Array.from(new Set(reqs.map((r) => r.status_name))).map((s) => [s, s]), "", "All Statuses"));
    const category = el("select", { "aria-label": "Category" }, A.options(Object.entries(CATEGORIES), "", "All Categories"));
    const crit = el("select", { "aria-label": "Criticality" }, A.options(["A", "B", "C", "D", "E"].map((x) => [x, "Criticality " + x]), "", "All Criticalities"));
    const kind = el("select", { "aria-label": "Nature" }, A.options(Object.entries(KINDS).map(([k, l]) => [k, l + "s"]), "",
      "Requirements et needs"));
    const phase = el("select", { "aria-label": "Life-Cycle Phase" },
      A.options(Object.entries(LIFECYCLE).concat([["-", "Non classée"]]), "", "All Phases"));
    /* D-B-059: traceability filters -- modified since a date, by a 3-letter key */
    const since = el("input", { type: "date", "aria-label": "Modifiée depuis le", title: "Modifiée depuis le" });
    const who = el("select", { "aria-label": "Modifiée par" }, A.options(Array.from(new Set(reqs
      .map((r) => r.last_change && r.last_change.by).filter(Boolean))).sort().map((x) => [x, "Modifiée par " + x]), "", "Modifiée par…"));
    /* D-B-071: responsible -- mine, unassigned (generic), or one person */
    const owner = el("select", { "aria-label": "Assignee" }, A.options([["me", "À moi"], ["none", "Non attribuées"]]
      .concat(Array.from(new Map(reqs.filter((r) => r.assignee_id).map((r) => [String(r.assignee_id), r.assignee_name])).entries())
        .sort((a, b) => a[1].localeCompare(b[1]))), "", "All Assignees"));
    const functionsSel = el("select", { "aria-label": "Function" }, A.options(Array.from(new Set(reqs.flatMap((r) =>
      (r.functions || "").split(", ").filter(Boolean)))).sort().map((f) => [f, f]).concat([["-", "No Function"]]), "", "All Functions"));
    const nf = A.needFields.filters(reqs);  // D-B-086
    const result = el("div");
    const counter = el("div", { class: "gm-count", role: "status", "aria-live": "polite" });
    const controlsByName = Object.assign({ q, kind, status, category, phase, crit, owner, since, who, functionsSel }, nf.byName);
    /* filters survive a reload (after an import) and a return to the screen, per Space, for this page session */
    const saved = FILTERS[ctx.pid] || {};
    Object.entries(controlsByName).forEach(([name, input]) => { if (saved[name]) input.value = saved[name]; });
    const clearBtn = el("button", { type: "button", class: "link-btn", onclick: () => {
      Object.values(controlsByName).forEach((input) => { input.value = ""; });
      draw();
    } }, "Effacer les filtres");
    const banner = DA.mineBanner && DA.mineBanner();
    if (banner && banner.firstChild && banner.firstChild.nodeType === 3) {  // Goldmine wording of the shared banner (D-B-071)
      banner.firstChild.textContent = "Filtre « Mes éléments » actif : vos requirements et tout le contenu générique "
        + "(non attribué) ; seules celles d'un collègue sont masquées. ";
    }
    page.append(banner || "", el("div", { class: "ag-filters" }, q, kind, status, category, phase, functionsSel, crit, owner,
      el("label", { class: "gm-since" }, "Modifiée depuis ", since), who, ...Object.values(nf.byName)), counter, result);

    function showCount(list) {
      const needs = list.filter((r) => r.kind === "need").length;
      const filtered = list.length !== reqs.length;
      const me = DA.session.user.id;
      const toMe = list.filter((r) => r.assignee_id === me).length;
      clear(counter);
      counter.classList.toggle("gm-count-filtered", filtered);
      counter.append(el("strong", null, filtered ? list.length + " retenue(s) sur " + reqs.length : list.length + " au total"),
        " · " + (list.length - needs) + " requirement(s) · " + needs + " need(s) · "
          + list.filter((r) => r.status_name === "Verified").length + " verified · ",
        el("span", { class: "gm-count-mine" }, toMe + " à moi"), " · " + list.filter((r) => !r.assignee_id).length + " non attribuée(s)"
          + (DA.myItems && DA.myItems() ? " (Mes éléments : les vôtres et les génériques)" : ""),
        filtered && Object.values(controlsByName).some((i) => i.value) ? clearBtn : "");
      exportBtn.textContent = filtered ? "Exporter la sélection (" + list.length + ") (CSV)" : "Exporter les requirements (" + reqs.length + ") (CSV)";
      exportBtn.disabled = !list.length;
      exportBtn.title = filtered ? "Seulement les lignes affichées, pour travailler par petits lots dans Excel" : "";
      exportAll.textContent = "Tout exporter (" + reqs.length + ")";
      exportAll.hidden = !filtered;
    }

    function draw() {
      FILTERS[ctx.pid] = Object.fromEntries(Object.entries(controlsByName).map(([n, i]) => [n, i.value]));
      const text = q.value.trim().toLowerCase();
      const me = DA.session.user.id;
      /* « Mes éléments » (D-B-033, D-B-071): what is assigned to me + the generic content nobody owns;
         only what belongs to someone else is hidden */
      const mine = DA.myItems && DA.myItems();
      const list = reqs.filter((r) => (!mine || !r.assignee_id || r.assignee_id === me)
        && (!owner.value || (owner.value === "me" ? r.assignee_id === me : owner.value === "none" ? !r.assignee_id
          : String(r.assignee_id) === owner.value))
        && (!status.value || r.status_name === status.value)
        && (!category.value || r.category === category.value) && (!crit.value || r.criticality === crit.value)
        && (!kind.value || r.kind === kind.value)
        && (!phase.value || (phase.value === "-" ? !r.lifecycle : r.lifecycle === phase.value))
        && (!who.value || (r.last_change && r.last_change.by === who.value))
        && (!functionsSel.value || (functionsSel.value === "-" ? !r.functions : (r.functions || "").split(", ").includes(functionsSel.value)))
        && (!since.value || (r.last_change && localDay(r.last_change.at) >= since.value)) && nf.test(r)
        && (!text || [r.key, r.external_id, r.statement, r.title, r.allocation, r.test_ref, r.functions]
          .join(" ").toLowerCase().includes(text)));
      shown = list;
      showCount(list);
      clear(result);
      result.append(DA.table(["Key", "External ID", "Requirement", "Category", "Phase", "Crit.", "Verif.", "Test Procedure", "Status",
        "Assignee", "Implémentée par", "Verif. Ref.", "Dernière modif."],
        list.map((r) => el("tr", { class: [r.lifecycle ? "gm-row-lc gm-lc-" + r.lifecycle : "",
          r.assignee_id === DA.session.user.id ? "gm-row-mine" : ""].join(" ").trim() || null },
          el("td", { class: "nowrap" }, el("a", { class: "ag-key", href: A.href(ctx, "issue/" + r.number) }, r.key)),
          el("td", { class: "nowrap" }, r.external_id || el("span", { class: "muted" }, "—")),
          el("td", { class: "gm-statement" }, r.kind === "need" ? el("span", { class: "badge gm-need" }, "Need") : null,
            DA.review.chip(r.standard_review),
            el("strong", null, r.title), r.statement && r.statement !== r.title ? el("div", { class: "muted" }, r.statement) : null,
            traceLine(ctx, r), A.needFields.chips(r)),
          el("td", null, CATEGORIES[r.category] || r.category),
          el("td", null, phaseChip(r.lifecycle)),
          el("td", null, r.criticality || "—"),
          el("td", { title: methodText(r.verification_method) }, r.verification_method || el("span", { class: "gm-missing" }, "?")),
          el("td", { class: "gm-tests" }, r.kind === "need" ? el("span", { class: "muted" }, "—")
            : r.test_ref ? r.test_ref.split(", ").flatMap((id, i) => [i ? " " : "", el("a", { class: "ag-key", href: "#/testing/" + ctx.key + "/test/" + id }, id)])
              : el("span", { class: "gm-missing", title: "Obligatoire : Modifier → Test Procedure" }, "?")),
          el("td", null, A.statusBadge(r.status_name, r.status_category)),
          el("td", { class: "nowrap" }, r.assignee_id === DA.session.user.id ? el("strong", { class: "gm-mine" }, "Moi")
            : r.assignee_name || el("span", { class: "muted", title: "Contenu générique : personne n'en est responsable" }, "—")),
          el("td", null, r.implemented_by.length ? r.implemented_by.flatMap((k, i) => [i ? ", " : "", el("a", { class: "ag-key",
            href: "#/agile/" + k.split("-")[0] + "/issue/" + k.split("-")[1] }, k)]) : el("span", { class: "muted" }, "—")),
          el("td", null, r.verification_ref || el("span", { class: "muted" }, "—")),
          el("td", { class: "nowrap gm-last", title: r.last_change ? r.last_change.name + " · " + DA.formatDate(r.last_change.at) : "" },
            r.last_change ? r.last_change.stamp : "—")))));
    }
    q.addEventListener("input", draw);
    [kind, status, category, phase, crit, owner, since, who, functionsSel, ...Object.values(nf.byName)]
      .forEach((s) => s.addEventListener("change", draw));
    draw();
  }

  /* ---------- Requirement block on the ticket page ---------- */
  function requirementBlock(ctx, issue, editable, reload) {
    if (!issue.is_requirement || !issue.requirement) return null;
    const r = issue.requirement;
    const box = el("div", { class: "ag-block gm-block" });
    function show() {
      clear(box);
      const row = (label, value) => el("div", { class: "gm-row" }, el("span", { class: "ag-field-label" }, label),
        el("span", null, value || el("span", { class: "muted" }, "—")));
      box.append(el("div", { class: "ag-block-head" }, el("h2", null, "Fiche requirement"),
        editable ? el("button", { type: "button", class: "link-btn", onclick: edit }, "Modifier") : null),
      DA.review.box({ state: r.standard_review, checked: r.standard_checked, standard: r.source_doc, editable, blocks: "Accepted",
        url: base(ctx) + "/issues/" + issue.number + "/standard-check", done: reload }),
      r.statement ? el("blockquote", { class: "gm-quote" }, r.statement) : el("p", { class: "gm-missing" }, "Statement manquant."),
      el("div", { class: "gm-grid" },
        row("Nature", KINDS[r.kind] || r.kind), row("Stakeholder", STAKEHOLDERS[r.stakeholder] || r.stakeholder),
        row("Derived From", r.derived_from),
        row("External ID", r.external_id), row("Revision", r.revision),
        row("Source", (SOURCES[r.source] || r.source) + (r.source_doc ? " · " + r.source_doc : "")),
        row("Received", r.received_at), row("Category", CATEGORIES[r.category] || r.category),
        row("Life-Cycle Phase", r.lifecycle ? phaseChip(r.lifecycle) : ""),
        row("Criticality", r.criticality), row("Allocation", r.allocation),
        row("Verification Method", methodText(r.verification_method)),
        row("Functions", r.functions), ...A.needFields.rows(r, row),
        row("Test Procedure", r.kind === "need" ? "" : A.testLinks(r.test_ref)),
        row("Test Source", r.kind === "need" ? "" : r.test_source),
        row("Verification Ref.", r.verification_ref)),
      row("Acceptance Criteria", r.acceptance_criteria),
      row("Rationale", r.rationale));
    }
    function edit() {
      clear(box);
      const c = controls(r);
      const error = el("p", { class: "form-error", role: "alert" });
      box.append(el("h2", null, "Fiche requirement"), el("form", { class: "ag-form", onsubmit: async (ev) => {
        ev.preventDefault();
        try { await api.put(base(ctx) + "/issues/" + issue.number + "/requirement", c.values()); reload(); }
        catch (err) { error.textContent = err.message; }
      } }, c.layout(), error, el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn", onclick: show }, "Annuler"),
        el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer"))));
    }
    show();
    return box;
  }

  A.views.goldmine = goldmineView;
  A.requirementBlock = requirementBlock;
})();
