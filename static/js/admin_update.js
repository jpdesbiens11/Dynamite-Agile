/* Admin → « Update et sauvegardes » (core lot v0.21, D-A-049; three parts since core lot v0.26, D-B-094; one tab with
   five parts since core lot v0.28, D-B-105 -- Configuration and Sauvegardes joined it). #/admin/update/<part>:
   « ↺ Restaurer »: the 2 × 3 chances (static/js/admin_restore.js, DA.adminRestore).
   « Framework »: the code only (functions, menus, options), never the data.
     1. « Exporter le code pour Claude » -> zip (code + UPDATE_PROMPT.md + context + database structure, no data);
     2. Claude (Opus 5.5 or later) returns a zip of the code with UPDATE_CHANGES.json (one entry per change);
     3. « Vérifier le zip » -> technical report, then the step-by-step review (DA.updateReview): every change opened
        and approved, or refused with a reason (« Retour pour Claude »); all approved -> « Appliquer »;
     4. history; the 3 most recent copies of the code can be restored.
   « Configuration »: the settings file .md (static/js/admin_config.js).
   « Données » (with the backups of the Spaces) and « Site complet »: static/js/admin_update_data.js (DA.adminUpdateData). */
(function () {
  "use strict";
  const { api, el, clear, toast } = DA;
  const PARTS = [["restore", "↺ Restaurer", "0.50.1-update-restore"], ["framework", "Framework", null],
    ["config", "Configuration", null], ["data", "Données", null], ["site", "Site complet", null]];
  const TODO = [["Annuler une erreur (mise à jour ratée, données effacées)", "restore"],
    ["Installer une version officielle publiée", "framework"],
    ["Installer une nouvelle version préparée avec Claude", "framework"],
    ["Changer les comptes, les droits ou les réglages en un seul fichier", "config"],
    ["Sauvegarder, récupérer ou ajouter des Spaces", "data"], ["Déménager le site sur un autre serveur", "site"]];

  DA.adminUpdate = {
    async render(body, sub) {
      const part = PARTS.some(([k]) => k === sub) ? sub : "restore";
      const content = el("div");
      body.append(el("div", { class: "up-todo" }, el("h2", { "data-new": "0.50.1-update-todo" }, "Que voulez-vous faire ?"),
        el("ul", null, TODO.map(([label, k]) => el("li", null, el("a", { href: "#/admin/update/" + k,
          "aria-current": k === part ? "true" : null }, label), " → ", el("span", { class: "muted" }, PARTS.find((x) => x[0] === k)[1]))))),
      el("nav", { class: "subtabs up-parts", "aria-label": "Volets" }, PARTS.map(([k, label, tag]) => el("a", {
        href: "#/admin/update/" + k, class: "subtab" + (k === part ? " active" : ""), "aria-current": k === part ? "page" : null,
        "data-new": tag }, label))), content);
      if (part === "restore") await DA.adminRestore.render(content);
      else if (part === "framework") framework(content, await api.get("/api/update/status"));
      else if (part === "config") await DA.adminExtra.loaders.config(content);
      else {
        await DA.adminUpdateData.render(content, part);
        if (part === "data") {  // D-B-105: the backups of the Spaces (ex-« Sauvegardes ») live with the data
          const backups = el("div", { class: "up-backups" });
          content.append(el("h2", { class: "up-sep" }, "Sauvegardes des Spaces (.zip)"), backups);
          await DA.adminExtra.loaders.backups(backups);
        }
      }
    },
  };

  function framework(box, s) {
    const report = el("div", { class: "up-report", "aria-live": "polite" });
    const file = el("input", { type: "file", accept: ".zip,application/zip", hidden: true });
    file.addEventListener("change", async () => {
      if (!file.files[0]) return;
      clear(report);
      report.append(el("p", { class: "muted" }, "Vérification de « " + file.files[0].name + " »…"));
      try { showReport(report, await api.upload("/api/update/check", file.files[0])); }
      catch (err) { clear(report); report.append(el("p", { class: "form-error" }, err.message)); }
      file.value = "";
    });
    box.append(DA.adminUpdateOnline ? DA.adminUpdateOnline.block() : null, DA.adminUpdateOfficial.block(s), el("div", { class: "up-steps" },
      el("section", { class: "up-step" }, el("h2", null, "1. Exporter le code pour Claude"),
        el("p", null, "Un seul fichier zip : le code, le prompt de départ (UPDATE_PROMPT.md), le contexte de la mise en service et la "
          + "structure de la base, sans aucune donnée. À donner à " + s.min_claude + " ou plus récent, avec les instructions du projet."),
        el("a", { class: "btn btn-primary", href: "/api/update/export.zip", download: "" }, "Exporter le code (.zip) — v" + s.version)),
      el("section", { class: "up-step" }, el("h2", null, "2. Importer le zip rendu par Claude"),
        el("p", null, "D'abord la vérification technique, puis la revue : chaque changement déclaré par Claude (UPDATE_CHANGES.json) "
          + "s'ouvre avec ses différences ligne à ligne et s'approuve un par un. Un seul refus arrête tout et produit un retour pour "
          + "Claude. Le site garde une sauvegarde du code et de la base avant d'appliquer."),
        el("button", { type: "button", class: "btn btn-primary", "data-new": "0.49.0-update-review", onclick: () => file.click() },
          "Vérifier un zip de mise à jour…"), file)),
    report,
    el("details", { class: "up-prompt" }, el("summary", null, "Voir le prompt de départ (il est aussi dans le zip exporté)"),
      el("pre", null, s.prompt)),
    el("h2", null, "Historique des mises à jour"),
    s.history.length ? DA.table(["Date", "De → vers", "Par", "Fichiers", "Sauvegarde", ""], s.history.map((h) => el("tr", null,
      el("td", null, (h.applied_at || "").replace("T", " ").slice(0, 16)),
      el("td", null, h.from + " → " + h.version + (h.action === "rollback" ? " (retour)" : h.action === "site_move" ? " (déménagement)" : "")),
      el("td", null, h.by), el("td", null, "+" + h.added + " · ~" + h.changed + " · −" + h.removed),
      el("td", null, h.code_backup || ""),
      el("td", null, h.code_backup && h.available ? el("button", { type: "button", class: "link-btn",
        onclick: () => rollback(h.code_backup, h.from) }, "Revenir à la " + h.from)
        : el("span", { class: "muted" }, h.code_backup ? "copie effacée (3 gardées)" : ""))))) : el("p", { class: "muted" },
      "Aucune mise à jour appliquée depuis ce serveur."));
  }

  function list(title, part) {
    return part.count ? el("details", null, el("summary", null, title + " (" + part.count + ")"),
      el("ul", null, part.sample.map((f) => el("li", null, f)), part.count > part.sample.length ? el("li", null, "…") : null)) : null;
  }

  function showReport(box, r) {
    clear(box);
    box.append(el("div", null, el("h2", null, "Version " + r.current + " → " + (r.version || "?")),
      list("Fichiers ajoutés", r.added), list("Fichiers modifiés", r.changed), list("Fichiers retirés", r.removed),
      DA.adminUpdateOfficial.report(r),
      r.log ? el("details", null, el("summary", null, "Journal de la mise à jour (UPDATE_LOG.md)"), el("pre", null, r.log)) : null));
    if (!r.ok) {
      box.append(el("div", { class: "form-error" }, el("strong", null, "Mise à jour refusée — " + r.problems.length + " problème(s) :"),
        el("ul", null, r.problems.map((p) => el("li", null, p)))));
      return;
    }
    const review = el("div");
    box.append(el("div", { class: "up-ok-line" }, el("p", { class: "up-ok" }, "✓ Vérification technique réussie. Revue pas à pas : "
      + r.review.total + " étape(s) à approuver" + (r.official ? " (une par version)." : ".")),
    DA.adminUpdateOfficial.later(r, () => clear(box))), review);
    DA.updateReview.show(review, {
      base: "/api/update/review/" + r.token, summary: r.review, applyLabel: "Appliquer la mise à jour " + r.version,
      confirm: "Appliquer la version " + r.version + " ? Le site redémarre (environ 10 secondes).",
      apply: () => api.post("/api/update/apply", { token: r.token }),
      onApplied: (done) => {
        toast("Version " + done.version + " installée. Copie du code : " + done.backup + " ; point de restauration des données : "
          + done.point + (done.restarting ? ". Redémarrage…" : "."), "success");
        if (done.restarting) setTimeout(() => location.reload(), 8000);
      },
    });
  }

  async function rollback(backup, version) {
    if (!confirm("Revenir au code de la version " + version + " ? Les données restent telles qu'elles sont.")) return;
    try {
      const done = await api.post("/api/update/rollback", { backup });
      toast("Code de la " + done.version + " restauré" + (done.restarting ? ". Redémarrage…" : "."), "success");
      if (done.restarting) setTimeout(() => location.reload(), 8000);
    } catch (err) { toast(err.message, "error"); }
  }
})();
