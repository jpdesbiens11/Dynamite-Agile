/* Administration → « Configuration » (core lot v0.11, D-B-047): the platform
   settings (never the content of the tabs) as a light Markdown file --
   download, tune with an approved AI assistant, load back with a preview of
   the differences; dated versions kept 3 months, any of them re-applicable. */
(function () {
  "use strict";

  const { api, el, clear, toast, modal, field, formatDate } = DA;

  function preview(res, onApply) {
    const rows = res.changes.map((c) => el("tr", { class: c.ok === false ? "rules-row-bad" : null },
      el("td", null, c.section), el("td", null, c.item), el("td", null, c.change)));
    const apply = el("button", { type: "button", class: "btn btn-primary", disabled: !res.changes.some((c) => c.ok !== false) },
      "Appliquer ces changements");
    let close = null;
    apply.addEventListener("click", async () => { apply.disabled = true; try { await onApply(); close(); } catch (err) { toast(err.message, "error"); apply.disabled = false; } });
    close = modal(res.dry_run ? "Aperçu des différences" : "Configuration appliquée", el("div", { class: "form" },
      el("p", { class: "muted" }, res.changes.length ? res.changes.length + " différence(s) avec la plateforme. Un instantané de l'état "
        + "actuel est gardé avant d'appliquer (on peut y revenir)." : "Aucune différence : la plateforme a déjà cette configuration."),
      rows.length ? DA.table(["Section", "Élément", "Changement"], rows) : null,
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Fermer"),
        res.dry_run ? apply : null)));
    const dialog = document.querySelector(".modal:last-of-type");
    if (dialog) dialog.classList.add("qa-import-modal");
  }

  function showResult(res) {
    const created = res.changes.filter((c) => /mot de passe temporaire/.test(c.change));
    toast("Configuration appliquée : " + res.changes.length + " changement(s)" + (res.stored ? ", gardée sous " + res.stored : "")
      + (res.purged ? ", " + res.purged + " version(s) de plus de 3 mois effacée(s)" : "") + ".", "success");
    if (created.length) modal("Comptes créés", el("div", null, created.map((c) => el("p", { class: "temp-password" }, c.item + " — " + c.change))));
  }

  async function render(body) {
    const data = await api.get("/api/admin/config");
    clear(body);
    const reload = () => render(body);
    const file = el("input", { type: "file", accept: ".md,text/markdown,text/plain" });
    const note = el("input", { type: "text", maxlength: 200, placeholder: "ex. réglages proposés par l'assistant IA pour le filigrane" });
    body.append(
      el("div", { class: "panel" }, el("h2", null, "1. Télécharger la configuration actuelle"),
        el("p", { class: "muted" }, "Un fichier .md léger : confidentialité, comptes et droits, Timesheet, préférences des comptes "
          + "(applicables), Spaces, workflows Agile et diagnostic (lecture seule). Aucun contenu des onglets. À discuter seulement "
          + "avec un assistant IA approuvé par votre établissement : il contient les noms des comptes."),
        el("a", { class: "btn btn-primary", href: "/api/admin/config/current.md", download: "", onclick: () => setTimeout(reload, 800) },
          "⇩ Télécharger la configuration (.md)")),
      el("div", { class: "panel" }, el("h2", null, "2. Charger une configuration modifiée"),
        el("p", { class: "muted" }, "Le fichier est lu, les différences sont affichées, puis appliquées sur confirmation. Il est gardé "
          + "sous le nom « config_JJMMAAAA-HHMMSS.md ». Les versions de plus de 3 mois sont effacées à ce moment."),
        el("div", { class: "form-row" }, field("Fichier .md", file), field("Note (optionnel)", note),
          el("button", { type: "button", class: "btn", onclick: async () => {
            if (!file.files[0]) { toast("Choisissez le fichier .md.", "error"); return; }
            const text = await file.files[0].text();
            try {
              const res = await api.post("/api/admin/config/import", { text, note: note.value, dry_run: true });
              preview(res, async () => { showResult(await api.post("/api/admin/config/import", { text, note: note.value, dry_run: false })); reload(); });
            } catch (err) { toast(err.message, "error"); }
          } }, "Voir les différences…"))),
      el("h2", null, "Versions gardées (" + data.snapshots.length + ", " + data.retention_days + " jours au maximum)"),
      DA.table(["Version", "Type", "Par", "Le", "Note", "Actions"], data.snapshots.map((s) => el("tr", null,
        el("td", { class: "code" }, s.name), el("td", null, s.source_label), el("td", null, s.by || "—"),
        el("td", { class: "nowrap" }, formatDate(s.created_at)), el("td", { class: "muted" }, s.note),
        el("td", null, el("div", { class: "actions" },
          el("a", { class: "btn btn-small", href: "/api/admin/config/" + s.id + ".md", download: "" }, "Télécharger"),
          el("button", { type: "button", class: "btn btn-small", onclick: async () => {
            try {
              const res = await api.post("/api/admin/config/" + s.id + "/apply", { dry_run: true });
              preview(res, async () => { showResult(await api.post("/api/admin/config/" + s.id + "/apply", { dry_run: false })); reload(); });
            } catch (err) { toast(err.message, "error"); }
          } }, "Revenir à cette version…")))))));
  }

  DA.adminExtra = DA.adminExtra || { loaders: {} };
  DA.adminExtra.loaders.config = render;
})();
