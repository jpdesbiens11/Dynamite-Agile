/* Timesheet - financial spaces and Budget Lines (D-B-084), under « Spaces et organismes » (administrators only).
   A Funding Space groups the Budget Lines a Space offers in the time sheet; each code has a stable code
   (Excel exports, history), a label, « réclamable » (checked by default in the Excel export for the organisms) and
   « actif » (offered for new ranges). A code with hours is never deleted, only deactivated. */
(function () {
  "use strict";

  const { api, el, toast, modal, field } = DA;
  const TS = (DA.timesheet = DA.timesheet || {});
  const fmtH = (h) => (TS.hours ? TS.hours(h) : h + " h");

  function lineDialog(set, reload) {
    const code = el("input", { type: "text", maxlength: 10, required: true, placeholder: "ex. B-13, LAB-01" });
    const label = el("input", { type: "text", maxlength: 120, required: true, placeholder: "ex. Essais du prototype (subvention PARI)" });
    const claimable = el("input", { type: "checkbox", checked: true });
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        await api.post("/api/timesheet/budget/lines", { set_id: set.id, code: code.value, label: label.value, claimable: claimable.checked });
        close(); toast("Poste " + code.value.toUpperCase() + " ajouté.", "success"); reload();
      } catch (err) { error.textContent = err.message; }
    } }, el("div", { class: "form-row" }, field("Code", code, "Ne change plus ensuite (exports)"), field("Libellé", label)),
    el("label", { class: "check" }, claimable, "Réclamable aux organismes (coché par défaut dans l'export Excel)"), error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Ajouter la Budget Line")));
    close = modal("Nouveau Budget Line — " + set.label, form);
  }

  function setDialog(reload) {
    const label = el("input", { type: "text", maxlength: 120, required: true, placeholder: "ex. Programme PARI-CNRC 2027" });
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      try { await api.post("/api/timesheet/budget/sets", { label: label.value }); close(); toast("Code set créé.", "success"); reload(); }
      catch (err) { error.textContent = err.message; }
    } }, field("Nom du Funding Space", label, "Ajoutez ensuite ses codes, puis rattachez-y des Spaces (tableau ci-dessus)."), error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer")));
    close = modal("Nouveau Funding Space", form);
  }

  TS.budgetAdmin = async function (page, reload) {
    let data;
    try { data = await api.get("/api/timesheet/budget"); } catch (err) { return; }
    const save = async (url, changes, what) => {
      try { await api.patch(url, changes); toast(what + " enregistré.", "success"); }
      catch (err) { toast(err.message, "error"); reload(); }
    };
    page.append(el("div", { class: "page-head tt-budget-head" }, el("h2", null, "Funding Spaces et Budget Lines"),
      el("p", { class: "muted" }, "Les codes que chacun choisit dans sa feuille de temps (selon le Funding Space du "
        + "Space) et que l'on réclame aux organismes dans l'Export Excel. Le code ne change jamais ; un code qui a des heures se "
        + "désactive au lieu d'être supprimé (il reste dans les feuilles et les exports)."),
      el("div", { class: "tt-budget-actions" },
        el("button", { type: "button", class: "btn btn-small", onclick: () => setDialog(reload) }, "+ Nouveau Funding Space"),
        el("a", { class: "btn btn-small", href: "/api/timesheet/budget/export.xlsx", download: "", "data-new": "0.50.0-funding-xlsx" }, "Exporter tous (.xlsx)"),
        TS.fundingImport ? TS.fundingImport(reload) : null)));  // D-B-101
    Object.entries(data.sets).forEach(([key, set]) => {
      const name = el("input", { type: "text", value: set.label, maxlength: 120, class: "tt-set-name", "aria-label": "Nom du Funding Space" });
      name.addEventListener("change", () => save("/api/timesheet/budget/sets/" + set.id, { label: name.value }, "Funding Space"));
      const on = el("input", { type: "checkbox", checked: set.active, "aria-label": "Funding Space actif" });
      on.addEventListener("change", async () => { await save("/api/timesheet/budget/sets/" + set.id, { active: on.checked }, "Funding Space"); reload(); });
      const rows = set.tasks.map((t) => {
        const label = el("input", { type: "text", value: t.label, maxlength: 120, "aria-label": "Libellé de " + t.key });
        const claim = el("input", { type: "checkbox", checked: t.claimable, "aria-label": "Réclamable " + t.key });
        const act = el("input", { type: "checkbox", checked: t.active, "aria-label": "Actif " + t.key });
        const url = "/api/timesheet/budget/lines/" + t.id;
        label.addEventListener("change", () => save(url, { label: label.value }, t.key));
        claim.addEventListener("change", () => save(url, { claimable: claim.checked }, t.key));
        act.addEventListener("change", () => save(url, { active: act.checked }, t.key));
        return el("tr", { class: t.active ? null : "tt-archived" }, el("td", null, el("strong", null, t.key)), el("td", null, label),
          el("td", { class: "tt-center" }, claim), el("td", { class: "tt-center" }, act),
          el("td", { class: "tt-num" }, t.ranges ? fmtH(t.hours) + " · " + t.ranges + " plage(s)" : "—"),
          el("td", null, t.ranges ? null : el("button", { type: "button", class: "link-btn", onclick: async () => {
            try { await api.del(url); toast(t.key + " supprimé.", "success"); reload(); } catch (err) { toast(err.message, "error"); }
          } }, "Supprimer")));
      });
      page.append(el("section", { class: "tt-set" + (set.active ? "" : " tt-archived") },
        el("div", { class: "tt-set-head" }, name, el("label", { class: "check" }, on, "Actif"),
          el("span", { class: "muted tt-small" }, set.spaces.length ? "Spaces : " + set.spaces.join(", ") : "Aucun Space rattaché"),
          el("span", { class: "tt-spacer" }),
          el("a", { class: "btn btn-small", href: "/api/timesheet/budget/sets/" + set.id + "/export.xlsx", download: "" }, "Exporter (.xlsx)"),
          el("button", { type: "button", class: "btn btn-small", onclick: () => lineDialog(set, reload) }, "+ Ajouter une Budget Line")),
        DA.table(["Code", "Libellé", "Réclamable", "Actif", "Heures saisies", ""], rows)));
    });
  };
})();
