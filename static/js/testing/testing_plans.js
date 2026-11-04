/* Test plans for an external supplier (D-A-048).
   #/testing/plans         -> the plans (code, supplier, tests, status)
   #/testing/plans/<code>  -> one plan: supplier (Test Location list), tests, purpose, life cycle, Word, results PDF
   A plan is made from the tests shown in the Test Base (« Créer un plan de test avec la sélection »). The Word
   document takes the existing procedures (wiki) and test records; the rest is marked « À COMPLÉTER ». */
(function () {
  "use strict";
  const { api, el, field, toast, modal } = DA;
  const T = (DA.testing = DA.testing || {});
  const STATUS_CLASS = { draft: "neutral", sent: "warn", results: "info", closed: "ok", cancelled: "danger" };
  const badge = (code, label) => el("span", { class: "badge badge-" + (STATUS_CLASS[code] || "neutral") }, label);

  T.newPlan = async function (testIds) {
    if (!testIds.length) return;
    const data = await api.get(T.api("/api/testing/plans"));
    const supplier = el("select", { required: true }, el("option", { value: "" }, "Choisir le fournisseur…"),
      data.locations.map((l) => el("option", { value: l.code }, l.label + " (" + l.code + ")")));
    const title = el("input", { type: "text", maxlength: 200, value: "Test Plan", required: true });
    const purpose = el("textarea", { rows: 3, maxlength: 4000, placeholder: "Contexte, article testé, but de la campagne (sinon « À COMPLÉTER » dans le document)" });
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        const made = await api.post(T.api("/api/testing/plans"), { title: title.value, location: supplier.value, purpose: purpose.value, tests: testIds });
        close(); toast("Plan " + made.code + " créé (Draft).", "success");
        location.hash = T.href("plans/" + made.code);
      } catch (err) { error.textContent = err.message; }
    } }, el("p", { class: "muted" }, testIds.length + " test(s) : " + testIds.slice(0, 12).join(", ") + (testIds.length > 12 ? "…" : "")),
    field("Fournisseur de test (liste Test Location)", supplier), field("Titre du plan", title), field("Objet (facultatif)", purpose), error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer le plan")));
    close = modal("Nouveau plan de test", form);
  };

  T.plansView = async function (main) {
    const data = await api.get(T.api("/api/testing/plans"));
    main.append(el("div", { class: "page-head" }, el("h1", null, "Test Plans (fournisseurs externes)"),
      el("p", { class: "muted" }, "Un plan par fournisseur : créez-le depuis la Test Base (filtres, puis « Créer un plan de test avec la "
        + "sélection »), exportez-le en Word, envoyez-le, joignez le PDF des résultats, puis fermez. Draft → Sent to Supplier → "
        + "Results Received → Closed.")));
    if (!data.plans.length) {
      main.append(el("div", { class: "empty" }, el("p", null, "Aucun plan. Filtrez la Test Base (ex. Subject « Electrical Safety », "
        + "texte « hipot ») puis « Créer un plan de test avec la sélection »."), el("a", { class: "btn btn-primary", href: T.href("") }, "Aller à la Test Base")));
      return;
    }
    main.append(DA.table(["Plan", "Titre", "Fournisseur", "Tests", "Status", "Résultats", "Créé par"], data.plans.map((p) => el("tr", null,
      el("td", null, el("a", { class: "ag-key", href: T.href("plans/" + p.code) }, p.code)), el("td", null, p.title),
      el("td", null, p.location_label), el("td", { class: "tg-num" }, String(p.tests.length)), el("td", null, badge(p.status, p.status_label)),
      el("td", null, p.has_results ? "PDF joint" : "—"), el("td", null, p.author || "")))));
  };

  T.planView = async function (main, code) {
    const [data, all] = await Promise.all([api.get(T.api("/api/testing/plans/" + code)), api.get(T.api("/api/testing/plans"))]);
    const p = data.plan;
    const reload = () => window.dispatchEvent(new HashChangeEvent("hashchange"));
    const draft = p.status === "draft";
    const loc = el("select", { disabled: !draft, "aria-label": "Fournisseur" }, all.locations.map((l) => el("option", { value: l.code, selected: l.code === p.location }, l.label)));
    const title = el("input", { type: "text", maxlength: 200, value: p.title });
    const purpose = el("textarea", { rows: 3, maxlength: 4000, "data-new": "0.40.0-plan-purpose" });  // D-A-049 example
    purpose.value = p.purpose || "";
    const docno = el("input", { type: "text", maxlength: 40, value: p.docno || "", placeholder: p.code });
    const rev = el("input", { type: "text", maxlength: 10, value: p.rev || "A" });
    const save = el("button", { type: "button", class: "btn btn-small", onclick: async () => {
      const body = { title: title.value, purpose: purpose.value, docno: docno.value, rev: rev.value };
      if (draft) body.location = loc.value;
      try { await api.patch(T.api("/api/testing/plans/" + code), body); toast("Plan enregistré.", "success"); reload(); } catch (err) { toast(err.message, "error"); }
    } }, "Enregistrer");
    const move = (to) => async () => {
      try { await api.post(T.api("/api/testing/plans/" + code + "/status"), { status: to }); toast(code + " : " + data.statuses[to] + ".", "success"); reload(); }
      catch (err) { toast(err.message, "error"); }
    };
    const file = el("input", { type: "file", accept: "application/pdf,.pdf", hidden: true });
    file.addEventListener("change", async () => {
      if (!file.files[0]) return;
      try { await api.upload(T.api("/api/testing/plans/" + code + "/results"), file.files[0]); toast("Résultats joints : " + file.files[0].name, "success"); reload(); }
      catch (err) { toast(err.message, "error"); }
    });
    const missing = p.test_rows.filter((t) => !t.has_procedure).length;
    main.append(el("nav", { class: "tg-crumbs" }, el("a", { href: T.href("plans") }, "Test Plans"), " › " + p.code),
      el("div", { class: "page-head tp-head" }, el("div", null, el("h1", null, p.code + " · " + p.title + " — " + p.location_label),
        el("p", null, badge(p.status, p.status_label), p.has_results ? el("span", { class: "muted" }, " · résultats : " + p.results_name) : null)),
        el("div", { class: "tg-actions" },
          el("a", { class: "btn btn-small btn-primary", href: T.api("/api/testing/plans/" + code + "/plan.docx"), download: "" }, "Générer le plan (.docx)"),
          ["sent", "results"].includes(p.status) ? el("button", { type: "button", class: "btn btn-small", onclick: () => file.click() },
            p.has_results ? "Remplacer le PDF des résultats" : "Joindre les résultats (PDF)") : null, file,
          p.has_results ? el("a", { class: "btn btn-small", href: T.api("/api/testing/plans/" + code + "/results.pdf"), download: "" }, "Ouvrir le PDF") : null,
          p.moves.map((m) => el("button", { type: "button", class: "btn btn-small" + (m.to === "closed" || m.to === "sent" ? " btn-primary" : ""),
            onclick: move(m.to) }, "→ " + m.label)))),
      el("p", { class: "tg-notice" }, "Le document reprend les procédures existantes du wiki et les fiches des tests ; tout le reste y est marqué "
        + "« À COMPLÉTER » à rédiger à la main." + (missing ? " " + missing + " test(s) sans procédure de sujet : leur procédure est à rédiger." : "")
        + (p.status === "results" && !p.has_results ? "" : "") + (p.status !== "closed" && p.status !== "cancelled" ? " La fermeture exige le PDF des résultats." : "")),
      el("div", { class: "form-row" }, field("Fournisseur (Test Location)", loc), field("Titre", title)),
      field("Objet de la campagne", purpose), el("div", { class: "form-row" }, field("No de document", docno), field("Révision", rev)),
      el("div", { class: "form-actions tt-left" }, save),
      el("h2", null, "Tests du plan (" + p.test_rows.length + ")"),
      DA.table(["Test", "Title", "Standard · Section", "Method", "Procédure", "Status"], p.test_rows.map((t) => el("tr", null,
        el("td", null, el("a", { class: "ag-key", href: T.href("test/" + t.test_id) }, t.test_id)), el("td", null, t.title),
        el("td", null, (t.standard + " · " + t.section).replace(/ · $/, "")), el("td", null, t.method),
        el("td", null, t.has_procedure ? "Wiki" : el("span", { class: "tp-todo" }, "À rédiger")), el("td", null, T.statusBadge(t.status))))));
  };
})();
