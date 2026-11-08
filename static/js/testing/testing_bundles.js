/* Bundles per prototype and evidence of a test plan (0.60.90, D-O-096).
   Shown on the plan page (#/testing/plans/<code>) once the plan is sent: evidence files dropped in bulk (the filled-in
   report, lab reports, spreadsheets, photos...), then one bundle per prototype actually tested, with a result for each
   test (Passed / Passed with derogation / Failed / Abandoned), a justification, and the evidence that supports it.
   The plan cannot be closed until every bundle is complete (the server says what is missing). */
(function () {
  "use strict";
  const { api, el, toast, modal, field } = DA;
  const T = (DA.testing = DA.testing || {});
  const RESULT_CLASS = { passed: "ok", derogation: "warn", failed: "danger", abandoned: "neutral" };
  const size = (n) => (n >= 1048576 ? (n / 1048576).toFixed(1) + " Mo" : Math.max(1, Math.round(n / 1024)) + " Ko");

  T.execution = function (p, code, reload) {
    const base = T.api("/api/testing/plans/" + code);
    const live = ["sent", "results"].includes(p.status);
    const run = (job) => async (...args) => { try { await job(...args); } catch (err) { toast(err.message, "error"); } };

    const picker = el("input", { type: "file", multiple: true, hidden: true });
    picker.addEventListener("change", run(async () => {
      for (const f of picker.files) await api.upload(base + "/evidence", f);
      toast(picker.files.length + " fichier(s) déposé(s).", "success"); reload();
    }));
    const bundleSelect = (e) => {
      const sel = el("select", { "aria-label": "Bundle de " + e.name, disabled: !live, onchange: run(async () => {
        await api.patch(base + "/evidence/" + e.id, { bundle_id: sel.value ? Number(sel.value) : null }); reload();
      }) }, el("option", { value: "" }, "En vrac"), p.bundles.map((b) => el("option", { value: b.id, selected: b.id === e.bundle_id }, b.proto)));
      return sel;
    };
    const evidenceBlock = el("section", { "data-new": "0.60.90-plan-evidence" },
      el("h2", null, "Preuves (" + p.evidence.length + ")"),
      el("p", { class: "muted" }, "Déposez les fichiers en vrac : rapport du plan rempli (.docx ou .pdf), rapports de laboratoire, Excel, PowerPoint, "
        + "photos, journaux (.txt, .csv, .log, .zip). Ensuite, pointez-les depuis les résultats de chaque bundle."),
      live ? el("div", { class: "form-actions tt-left" }, el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => picker.click() }, "Déposer des fichiers…"), picker) : null,
      p.evidence.length ? DA.table(["Fichier", "Taille", "Déposé par", "Bundle", ""], p.evidence.map((e) => el("tr", null,
        el("td", null, el("a", { href: base + "/evidence/" + e.id + "/file", download: e.name }, e.name)), el("td", null, size(e.size)),
        el("td", null, e.by || ""), el("td", null, bundleSelect(e)),
        el("td", null, live ? el("button", { type: "button", class: "btn btn-small", onclick: run(async () => {
          await api.del(base + "/evidence/" + e.id); reload();
        }) }, "Retirer") : null)))) : el("p", { class: "muted" }, "Aucune preuve pour le moment."));

    const resultRow = (b, t) => {
      const cur = b.results[t.test_id] || { result: "", note: "", evidence: [] };
      const sel = el("select", { "aria-label": "Résultat " + t.test_id, disabled: !live },
        el("option", { value: "" }, "— à saisir —"), Object.entries(p.result_labels).map(([k, v]) => el("option", { value: k, selected: k === cur.result }, v)));
      const note = el("input", { type: "text", maxlength: 4000, value: cur.note, disabled: !live, placeholder: "Justification (dérogation, échec, abandon)", "aria-label": "Note " + t.test_id });
      const chosen = new Set(cur.evidence);
      const boxes = p.evidence.map((e) => el("label", { class: "tb-ev" }, el("input", { type: "checkbox", checked: chosen.has(e.id), disabled: !live,
        onchange: (ev) => { ev.target.checked ? chosen.add(e.id) : chosen.delete(e.id); save(); } }), " " + e.name));
      const save = run(async () => {
        await api.put(base + "/bundles/" + b.id + "/results/" + t.test_id, { result: sel.value, note: note.value, evidence: [...chosen] }); reload();
      });
      sel.addEventListener("change", save); note.addEventListener("change", save);
      return el("tr", null, el("td", null, el("a", { class: "ag-key", href: T.href("test/" + t.test_id) }, t.test_id), " " + t.title),
        el("td", { class: "tb-res tb-" + (RESULT_CLASS[cur.result] || "none") }, sel), el("td", null, note),
        el("td", null, boxes.length ? el("details", null, el("summary", null, chosen.size + " preuve(s)"), boxes) : el("span", { class: "muted" }, "aucune")));
    };
    const bundleBlock = (b) => {
      const done = p.test_rows.filter((t) => (b.results[t.test_id] || {}).result).length;
      return el("section", { class: "tb-bundle" }, el("h3", null, "Proto " + b.proto + (b.serial ? " · S/N " + b.serial : "") + " — " + done + " / " + p.test_rows.length + " résultats"),
        b.note ? el("p", { class: "muted" }, b.note) : null,
        live ? el("div", { class: "tg-actions" }, el("button", { type: "button", class: "btn btn-small", onclick: () => bundleForm(b) }, "Modifier"),
          el("button", { type: "button", class: "btn btn-small", onclick: run(async () => {
            if (!confirm("Supprimer le bundle " + b.proto + " et ses résultats ? Les preuves restent dans le plan.")) return;
            await api.del(base + "/bundles/" + b.id); reload();
          }) }, "Supprimer")) : null,
        DA.table(["Test", "Résultat", "Justification", "Preuves à l'appui"], p.test_rows.map((t) => resultRow(b, t))));
    };
    const bundleForm = (b) => {
      const proto = el("input", { type: "text", maxlength: 80, required: true, value: b ? b.proto : "", placeholder: "ex. P2-B07" });
      const serial = el("input", { type: "text", maxlength: 80, value: b ? b.serial : "", placeholder: "Numéro de série (facultatif)" });
      const note = el("textarea", { rows: 2, maxlength: 2000 }); note.value = b ? b.note : "";
      const error = el("p", { class: "form-error", role: "alert" });
      let close = null;
      const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
        ev.preventDefault();
        try {
          const body = { proto: proto.value, serial: serial.value, note: note.value };
          if (b) await api.patch(base + "/bundles/" + b.id, body); else await api.post(base + "/bundles", body);
          close(); reload();
        } catch (err) { error.textContent = err.message; }
      } }, field("Prototype testé (identifiant)", proto), field("Numéro de série", serial), field("Note (configuration, firmware, conditions)", note), error,
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
        el("button", { type: "submit", class: "btn btn-primary" }, b ? "Enregistrer" : "Créer le bundle")));
      close = modal(b ? "Modifier le bundle" : "Nouveau bundle (un par prototype testé)", form);
    };
    return el("div", { class: "tb-exec", "data-new": "0.60.90-plan-bundles" }, evidenceBlock,
      el("h2", null, "Bundles par prototype (" + p.bundles.length + ")"),
      el("p", { class: "muted" }, "Un bundle par prototype effectivement testé : chaque test du plan y reçoit un résultat. « Passed », « Passed with "
        + "derogation » et « Failed » exigent au moins une preuve ; tout sauf « Passed » exige une justification."),
      live ? el("div", { class: "form-actions tt-left" }, el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => bundleForm(null) }, "+ Bundle (prototype testé)")) : null,
      live && p.blockers.length ? el("div", { class: "tg-notice", role: "status" }, el("b", null, "Avant de fermer le plan :"), el("ul", null, p.blockers.slice(0, 8).map((m) => el("li", null, m)))) : null,
      !p.bundles.length ? el("p", { class: "muted" }, live ? "Aucun bundle." : "Aucun bundle : les bundles se saisissent une fois le plan envoyé au fournisseur.") : p.bundles.map(bundleBlock));
  };
})();
