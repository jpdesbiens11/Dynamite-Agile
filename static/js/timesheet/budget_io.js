/* Timesheet → Spaces et organismes: import of Funding Spaces from Excel (D-B-101).
   The workbook is read first; each Funding Space of the file is shown as « nouveau », « aucun changement » or the
   list of changes found, with its problems. Accept or refuse each one; « Appliquer » writes only the accepted ones.
   Codes never change, nothing is deleted. */
(function () {
  "use strict";
  const { api, el, toast, modal } = DA;
  const TS = (DA.timesheet = DA.timesheet || {});
  const STATUS = { new: ["Nouveau", "info"], changed: ["Modifié", "warn"], same: ["Aucun changement", "neutral"] };

  function review(res, reload) {
    const choice = {};
    let close = null;
    const count = el("strong");
    const apply = el("button", { type: "button", class: "btn btn-primary" });
    const refreshCount = () => {
      const n = Object.values(choice).filter(Boolean).length;
      count.textContent = n + " espace(s) accepté(s)";
      apply.textContent = "Appliquer les espaces acceptés (" + n + ")";
      apply.disabled = !n;
    };
    const items = res.spaces.map((s, i) => {
      const ok = !s.problems.length && s.status !== "same";
      choice[s.sheet] = ok;
      const name = "fs-" + i;
      const yes = el("input", { type: "radio", name, checked: ok, disabled: !ok });
      const no = el("input", { type: "radio", name, checked: !ok });
      yes.addEventListener("change", () => { choice[s.sheet] = true; refreshCount(); });
      no.addEventListener("change", () => { choice[s.sheet] = false; refreshCount(); });
      return el("section", { class: "fs-item" },
        el("h3", null, s.label || s.sheet, " ", DA.badge(STATUS[s.status][0], STATUS[s.status][1]),
          el("span", { class: "muted" }, "  feuille « " + s.sheet + " »")),
        s.changes.length ? el("ul", null, s.changes.map((c) => el("li", null, c))) : el("p", { class: "muted" }, "Rien à changer."),
        (s.kept || []).length ? el("p", { class: "muted" }, "Absents du fichier, gardés tels quels : " + s.kept.join(", ")) : null,
        s.problems.length ? el("div", { class: "form-error" }, el("strong", null, "Ne peut pas être accepté :"),
          el("ul", null, s.problems.map((p) => el("li", null, p)))) : null,
        s.status === "same" ? null : el("div", { class: "fs-choice" }, el("label", null, yes, " Accepter"), el("label", null, no, " Refuser")));
    });
    apply.addEventListener("click", async () => {
      apply.disabled = true;
      try {
        const done = await api.post("/api/timesheet/budget/import/" + res.token, { accept: Object.keys(choice).filter((k) => choice[k]) });
        close();
        toast(done.applied.length + " Funding Space(s) appliqué(s)" + (done.refused.length ? ", " + done.refused.length + " refusé(s) ou inchangé(s)" : "") + ".", "success");
        reload();
      } catch (err) { toast(err.message, "error"); apply.disabled = false; }
    });
    refreshCount();
    close = modal("Import des Funding Spaces — revue", el("div", { class: "fs-review" },
      el("p", { class: "muted" }, "Acceptez ou refusez chaque Funding Space. Les codes ne changent jamais et rien n'est supprimé."),
      items, el("div", { class: "form-actions" }, count, apply)));
  }

  TS.fundingImport = function (reload) {
    const file = el("input", { type: "file", accept: ".xlsx", hidden: true });
    file.addEventListener("change", async () => {
      const f = file.files[0];
      file.value = "";
      if (!f) return;
      try { review(await api.upload("/api/timesheet/budget/import", f), reload); }
      catch (err) { toast(err.message, "error"); }
    });
    return el("span", null, el("button", { type: "button", class: "btn btn-small", "data-new": "0.50.0-funding-import",
      onclick: () => file.click() }, "Importer (.xlsx)…"), file);
  };
})();
