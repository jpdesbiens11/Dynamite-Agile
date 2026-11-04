/* Goldmine - re-import of a specification with a preview (D-B-070).
   1. The file is sent in « preview » mode: the server runs the whole import,
      rolls it back and lists every stored value the file would replace.
   2. Nothing to overwrite -> applied at once (creations, unchanged lines).
   3. Otherwise ONE screen lists all the differing fields (count first),
      each with a box: checked = take the file value, unchecked = keep the
      value in Goldmine (a manual correction, for instance).
   4. A second, final confirmation repeats the counts; only then is the
      import applied, with the unchecked fields kept. */
(function () {
  "use strict";

  const { api, el, toast } = DA;
  const A = DA.agile;

  const plural = (n, one, many) => n + " " + (n > 1 ? many : one);

  function url(ctx) { return "/api/agile/p/" + ctx.pid + "/import/requirements"; }

  function widen(cls) {
    const dialogs = document.querySelectorAll(".modal");
    dialogs[dialogs.length - 1].classList.add(cls);
  }

  async function apply(ctx, csv, note, keep, confirmed, reload) {
    try {
      const result = await api.post(url(ctx), { csv, mode: "apply", keep, confirm_overwrites: confirmed });
      A.importReportModal(result, note);
      if (result.kept) toast(plural(result.kept, "valeur conservée", "valeurs conservées") + " dans Goldmine.", "success");
      if (reload) reload();
    } catch (err) {
      DA.modal("Import impossible", el("div", { class: "ag-import-report" },
        el("div", { class: "ag-import-advice ag-import-advice-bad" }, el("strong", null, err.message))));
    }
  }

  /* Second question: same numbers, last chance to go back. */
  function finalConfirm(ctx, csv, note, keep, taken, keptCount, rows, reload) {
    let close = null;
    const body = el("div", { class: "ag-import-report" },
      el("div", { class: "ag-import-advice ag-import-advice-bad" },
        el("strong", null, "Confirmation finale : " + plural(taken, "champ sera écrasé", "champs seront écrasés")
          + " dans " + plural(rows, "requirement", "requirements") + "."),
        el("p", null, keptCount ? plural(keptCount, "champ décoché garde", "champs décochés gardent")
          + " la valeur actuelle de Goldmine." : "Aucun champ n'est conservé : toutes les valeurs du fichier remplacent "
          + "celles de Goldmine."),
        el("p", null, "L'historique de chaque requirement garde la trace du changement (qui, quand, champ).")),
      el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn", onclick: () => close() }, "Retour"),
        el("button", { type: "button", class: "btn btn-danger", onclick: () => {
          close();
          apply(ctx, csv, note, keep, taken, reload);
        } }, "Oui, écraser " + plural(taken, "champ", "champs"))));
    close = DA.modal("Écraser les valeurs de Goldmine ?", body);
  }

  /* First question: every difference at once, with its count. */
  function previewModal(ctx, csv, note, preview, reload) {
    const report = preview.report;
    const changed = report.filter((r) => r.differences.length);
    const count = (s) => report.filter((r) => r.status.startsWith(s)).length;
    const boxes = [];
    const tally = el("strong");
    const go = el("button", { type: "button", class: "btn btn-primary" });
    function refresh() {
      const taken = boxes.filter((b) => b.box.checked).length;
      tally.textContent = taken + " / " + boxes.length + " coché(s)";
      go.textContent = "Écraser " + plural(taken, "champ coché", "champs cochés") + "…";
    }
    const rows = changed.flatMap((r) => r.differences.map((d, i) => {
      const box = el("input", { type: "checkbox", checked: true, "aria-label": r.row + " · " + d.label,
        onchange: refresh });
      boxes.push({ box, line: String(r.line), field: d.field });
      return el("tr", { class: i === 0 ? "gm-diff-first" : null },
        el("td", null, box),
        el("td", { class: "nowrap muted" }, i === 0 ? String(r.line) : ""),
        el("td", { class: "nowrap" }, i === 0 ? r.row : ""),
        el("td", { class: "nowrap" }, d.label),
        el("td", { class: "gm-diff-old" }, d.current || el("span", { class: "muted" }, "(vide)")),
        el("td", { class: "gm-diff-new" }, d.new || el("span", { class: "muted" }, "(vide)")));
    }));
    const setAll = (on) => { boxes.forEach((b) => { b.box.checked = on; }); refresh(); };
    const refused = report.filter((r) => r.status === "refusée");
    let close = null;
    go.addEventListener("click", () => {
      const keep = {};
      boxes.filter((b) => !b.box.checked).forEach((b) => { (keep[b.line] = keep[b.line] || []).push(b.field); });
      const taken = boxes.filter((b) => b.box.checked).length;
      const rowsTouched = new Set(boxes.filter((b) => b.box.checked).map((b) => b.line)).size;
      close();
      if (!taken) { apply(ctx, csv, note, keep, 0, reload); return; }  // everything kept: nothing to overwrite
      finalConfirm(ctx, csv, note, keep, taken, boxes.length - taken, rowsTouched, reload);
    });
    refresh();
    close = DA.modal("Aperçu de l'import — champs différents", el("div", { class: "ag-import-report" },
      el("div", { class: "ag-import-advice gm-diff-advice" },
        el("strong", null, plural(preview.overwrites, "champ différent trouvé", "champs différents trouvés") + " dans "
          + plural(preview.overwrite_rows, "requirement", "requirements") + "."),
        el("p", null, "Coché : la valeur du fichier remplace celle de Goldmine. Décochez ce qui a été corrigé à la main "
          + "dans Goldmine et doit rester. Rien n'est encore écrit.")),
      el("div", { class: "ag-chips" }, [["créée", "à créer"], ["mise à jour", "à mettre à jour"], ["inchangée", "inchangée(s)"],
        ["refusée", "refusée(s)"]].filter(([s]) => count(s)).map(([s, l]) =>
        el("span", { class: "badge badge-" + (s === "refusée" ? "danger" : s === "inchangée" ? "neutral" : "ok") }, count(s) + " " + l))),
      note ? el("p", { class: "ag-import-warning" }, "⚠ " + note) : null,
      preview.note ? el("p", { class: "ag-import-warning" }, "⚠ " + preview.note) : null,
      refused.length ? el("p", { class: "ag-import-warning" }, "⚠ " + plural(refused.length, "ligne sera refusée", "lignes seront refusées")
        + " (lignes Excel " + refused.map((r) => r.line).join(", ") + ") : le détail et le correctif suivront l'import.") : null,
      el("div", { class: "gm-diff-tools" }, tally,
        el("button", { type: "button", class: "link-btn", onclick: () => setAll(true) }, "Tout cocher"),
        el("button", { type: "button", class: "link-btn", onclick: () => setAll(false) }, "Tout décocher (garder Goldmine)")),
      el("div", { class: "table-wrap ag-report" },
        DA.table(["Écraser", "Ligne Excel", "Requirement", "Champ", "Valeur actuelle (Goldmine)", "Valeur du fichier"], rows)),
      el("div", { class: "form-actions" },
        el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler l'import"), go)));
    widen("modal-report");
  }

  function importButton(ctx, label, reload) {
    const input = el("input", { type: "file", accept: ".csv,text/csv", class: "ag-hidden-frame" });
    const button = el("button", { type: "button", class: "btn btn-small", onclick: () => input.click() }, label);
    input.addEventListener("change", async () => {
      const file = input.files[0];
      input.value = "";
      if (!file) return;
      if (!/\.csv$/i.test(file.name)) {
        toast("« " + file.name + " » n'est pas un .csv. Dans Excel : Fichier → Enregistrer sous → "
          + "CSV UTF-8 (délimité par des virgules).", "error");
        return;
      }
      button.disabled = true;
      try {
        const { text, note } = await A.readCsvFile(file);
        const preview = await api.post(url(ctx), { csv: text, mode: "preview" });
        if (preview.overwrites) previewModal(ctx, text, note, preview, reload);
        else await apply(ctx, text, note, {}, 0, reload);  // nothing stored would be replaced
      } catch (err) {
        DA.modal("Import impossible", el("div", { class: "ag-import-report" },
          el("div", { class: "ag-import-advice ag-import-advice-bad" }, el("strong", null, err.message))));
      } finally {
        button.disabled = false;
      }
    });
    return el("span", null, input, button);
  }

  A.goldmineImportButton = importButton;
})();
