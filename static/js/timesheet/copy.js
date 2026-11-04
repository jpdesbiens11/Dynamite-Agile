/* Timesheet - copy dialogs (D-B-026): a range or a whole day to other days
   of the week, and a past week into the week shown. The copies are then
   fine-tuned in the table like any range. Loaded before timesheet.js. */
(function () {
  "use strict";

  const { api, el, toast, modal } = DA;
  const TS = (DA.timesheet = DA.timesheet || {});
  const fmtH = (h) => (TS.hours ? TS.hours(h) : h + " h");

  function report(copied) {
    let text = copied.created + " plage(s) copiée(s)";
    if (copied.removed) text += ", " + copied.removed + " remplacée(s)";
    if (copied.skipped) text += " — " + copied.skipped + " ignorée(s) (projet fermé aux feuilles de temps)";
    toast(text + ". Ajustez heures et descriptions au besoin.", copied.skipped ? "error" : "success");
  }

  /* Copy `ids` (ranges of day `fromDay`, or one range) to other days of the week. */
  TS.copyDaysDialog = function (data, ids, fromDay, what, done) {
    const boxes = data.days.map((d, i) => {
      const box = el("input", { type: "checkbox", value: d, disabled: d === fromDay });
      return el("label", { class: "check tt-copy-day" + (d === fromDay ? " tt-copy-source" : "") }, box,
        data.day_labels[i] + (d === fromDay ? " (source)" : "") + " · " + fmtH(data.totals[d]));
    });
    const pick = (fn) => boxes.forEach((b, i) => { const box = b.firstChild; if (!box.disabled) box.checked = fn(i); });
    let close = null;
    async function submit(ev) {
      ev.preventDefault();
      const to = boxes.map((b) => b.firstChild).filter((b) => b.checked).map((b) => b.value);
      if (!to.length) { toast("Cochez au moins un jour.", "error"); return; }
      try {
        const res = await api.post("/api/timesheet/copy/days", { entry_ids: ids, to_days: to });
        close(); report(res.copied); done();
      } catch (err) { toast(err.message, "error"); }
    }
    const form = el("form", { class: "form", onsubmit: submit },
      el("p", null, "Copier " + what + " vers :"),
      el("div", { class: "tt-copy-days" }, boxes),
      el("div", { class: "tt-copy-quick" },
        el("button", { type: "button", class: "btn btn-small", onclick: () => pick((i) => i < 5) }, "Lundi à vendredi"),
        el("button", { type: "button", class: "btn btn-small", onclick: () => pick(() => true) }, "Tous"),
        el("button", { type: "button", class: "btn btn-small", onclick: () => pick(() => false) }, "Aucun")),
      el("p", { class: "muted tt-small" }, "Projet, task, heures et description sont repris ; vous pourrez tout ajuster ensuite."),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
        el("button", { type: "submit", class: "btn btn-primary" }, "Copier")));
    close = modal("Copier vers d'autres jours", form);
  };

  /* Copy a past week into the week shown. */
  TS.copyWeekDialog = async function (data, done) {
    let recent;
    try { recent = (await api.get("/api/timesheet/copy/weeks")).weeks.filter((w) => w.week_start !== data.week.start); }
    catch (err) { toast(err.message, "error"); return; }
    if (!recent.length) { toast("Aucune semaine passée avec des plages à copier.", "error"); return; }
    const before = recent.find((w) => w.week_start < data.week.start) || recent[0];
    const radios = recent.map((w) => el("label", { class: "check tt-copy-week" },
      el("input", { type: "radio", name: "tt-src", value: w.week_start, checked: w === before }),
      "Semaine du " + w.week_start + " · " + w.ranges + " plage(s) · " + fmtH(w.total) + " · " + w.status_label));
    const hasRanges = data.entries.length > 0;
    const add = el("input", { type: "radio", name: "tt-mode", value: "add", checked: true });
    const replace = el("input", { type: "radio", name: "tt-mode", value: "replace" });
    let close = null;
    async function submit(ev) {
      ev.preventDefault();
      const source = (radios.map((r) => r.firstChild).find((r) => r.checked) || {}).value;
      try {
        const res = await api.post("/api/timesheet/copy/week", { start: data.week.start, source,
          mode: replace.checked ? "replace" : "add" });
        close(); report(res.copied); done();
      } catch (err) { toast(err.message, "error"); }
    }
    const form = el("form", { class: "form", onsubmit: submit },
      el("p", null, "Recopier les plages d'une semaine passée dans la semaine du " + data.week.start + ", jour pour jour (lundi → lundi…) :"),
      el("div", { class: "tt-copy-weeks" }, radios),
      hasRanges ? el("fieldset", { class: "tt-copy-mode" }, el("legend", null, "Cette semaine a déjà " + data.entries.length + " plage(s)"),
        el("label", { class: "check" }, add, "Ajouter les plages copiées"),
        el("label", { class: "check" }, replace, "Remplacer les plages de cette semaine")) : null,
      el("p", { class: "muted tt-small" }, "Les descriptions sont reprises telles quelles : relisez-les avant de soumettre."),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
        el("button", { type: "submit", class: "btn btn-primary" }, "Copier la semaine")));
    close = modal("Copier une semaine passée", form);
  };
})();
