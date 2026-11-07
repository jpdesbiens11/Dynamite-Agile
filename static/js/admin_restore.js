/* Admin → Update et sauvegardes → « ↺ Restaurer » (core lot v0.28, D-B-104): the « 2 × 3 chances ».
   Left: the 3 most recent copies of the code (Framework), « Revenir à la vX » (POST /api/update/rollback).
   Right: the 3 most recent restore points of the data (core/restorepoints.py): « Créer un point maintenant »,
   « Récupérer un Space… » (as a NEW Space) and « Revenir à ce point… » (the whole site, a point « avant retour » first).
   0.60.79: « Supprimer… » on both sides, with a double confirmation. */
(function () {
  "use strict";
  const { api, el, clear, toast, field, modal } = DA;
  const size = (n) => (n >= 1048576 ? (n / 1048576).toFixed(1) + " Mo" : Math.max(1, Math.round(n / 1024)) + " Ko");

  DA.adminRestore = {
    async render(box) {
      const data = await api.get("/api/admin/restore-points");
      clear(box);
      const reload = () => DA.adminRestore.render(box);
      box.append(el("p", { class: "muted" }, "Deux filets de sécurité, trois chances chacun : les " + data.keep + " dernières versions "
        + "du code (Framework) et les " + data.keep + " derniers points de restauration des données. Le code et les données se "
        + "restaurent séparément : revenir à une version du code ne change aucune donnée, et inversement."),
      el("div", { class: "rp-grid" }, framework(data, reload), points(data, reload)),
      el("p", { class: "muted rp-foot" }, "Un point de données est créé automatiquement avant chaque mise à jour du Framework, import "
        + "de données, configuration appliquée ou retour à un point, et une fois par jour à la première activité (l'état de la "
        + "veille au soir). Seuls les " + data.keep + " plus récents sont gardés : un nouveau point efface le plus ancien. Les "
        + "fichiers joints (images, PDF) restent sur le serveur ; ceux d'un Space supprimé sont dans sa sauvegarde « avant "
        + "suppression » (volet Données)."));
    },
  };

  /* 0.60.79 (D-O-085): erase a copy of the code or a point of the data, after two confirmations: a first message,
     then a window where SUPPRIMER is typed; the server also wants the exact name back. Nothing can bring it back. */
  function erase(what, url, name, reload) {
    if (!confirm("Supprimer " + what + " ? Cette sauvegarde ne pourra plus servir à revenir en arrière.")) return;
    const word = el("input", { type: "text", autocomplete: "off", "aria-label": "Tapez SUPPRIMER pour confirmer" });
    const go = el("button", { type: "button", class: "btn btn-danger", disabled: true }, "Supprimer définitivement");
    word.addEventListener("input", () => { go.disabled = word.value.trim() !== "SUPPRIMER"; });
    let close = null;
    go.addEventListener("click", async () => {
      go.disabled = true;
      try {
        await api.post(url, { confirm: name });
        close();
        toast("Supprimé : " + what + ".", "success");
        reload();
      } catch (err) { toast(err.message, "error"); go.disabled = false; }
    });
    close = modal("Deuxième confirmation", el("div", { class: "form" },
      el("p", null, el("strong", null, "Suppression définitive de " + what + ". "), "Aucune autre sauvegarde ne la remplace : "
        + "il restera une chance de moins de revenir en arrière. L'opération est inscrite au journal d'audit."),
      field("Tapez SUPPRIMER pour confirmer", word),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"), go)));
    word.focus();
  }

  function framework(data, reload) {
    const rows = data.framework.map((c) => el("tr", null,
      el("td", { class: "code" }, "v" + c.version), el("td", { class: "nowrap" }, c.saved_at),
      el("td", null, c.replaced_by ? "par la v" + c.replaced_by + (c.by ? " (" + c.by + ")" : "") : "—"),
      el("td", null, el("div", { class: "rp-actions" },
        el("button", { type: "button", class: "btn btn-small", onclick: () => rollback(c) }, "Revenir à la v" + c.version),
        el("button", { type: "button", class: "btn btn-small btn-danger", "data-new": "0.60.79-backup-delete",
          onclick: () => erase("la copie du code v" + c.version + " (gardée le " + c.saved_at + ")",
            "/api/admin/code-backups/" + c.backup + "/delete", c.backup, reload) }, "Supprimer…")))));
    return el("section", { class: "up-step rp-col" },
      el("h2", { "data-new": "0.50.1-restore-framework" }, "Framework — " + data.keep + " dernières versions du code"),
      el("p", null, "En service : ", el("strong", null, "v" + data.version), ". Chaque mise à jour garde une copie du code qu'elle "
        + "remplace."),
      rows.length ? DA.table(["Version", "Gardée le", "Remplacée", ""], rows)
        : el("p", { class: "muted" }, "Aucune copie du code pour l'instant : la première est faite à la prochaine mise à jour "
          + "(volet Framework)."));
  }

  async function rollback(c) {
    if (!confirm("Revenir au code de la version " + c.version + " ? Les données restent telles qu'elles sont ; un point de "
      + "restauration est créé d'abord. Le site redémarre (environ 10 secondes).")) return;
    try {
      const done = await api.post("/api/update/rollback", { backup: c.backup });
      toast("Code de la " + done.version + " restauré" + (done.restarting ? ". Redémarrage…" : "."), "success");
      if (done.restarting) setTimeout(() => location.reload(), 8000);
    } catch (err) { toast(err.message, "error"); }
  }

  function points(data, reload) {
    const note = el("input", { type: "text", maxlength: 200, placeholder: "ex. avant de réorganiser les tickets de EQP" });
    const rows = data.points.map((p) => el("tr", null,
      el("td", { class: "nowrap" }, el("strong", null, p.local)),
      el("td", null, p.label, p.note ? el("div", null, el("em", null, p.note)) : null,
        el("div", { class: "muted rp-meta" }, "par " + p.by + " · " + p.spaces + " Spaces · " + p.users + " comptes · " + size(p.size))),
      el("td", null, el("div", { class: "rp-actions" },
        el("button", { type: "button", class: "btn btn-small", onclick: () => spaceDialog(p, reload) }, "Récupérer un Space…"),
        el("button", { type: "button", class: "btn btn-small btn-danger", onclick: () => revertDialog(p) }, "Revenir à ce point…"),
        el("button", { type: "button", class: "btn btn-small btn-danger", "data-new": "0.60.79-backup-delete",
          onclick: () => erase("le point de restauration du " + p.local, "/api/admin/restore-points/" + p.name + "/delete", p.name, reload) },
          "Supprimer…")))));
    return el("section", { class: "up-step rp-col" },
      el("h2", { "data-new": "0.50.1-restore-data" }, "Données — " + data.keep + " points de restauration"),
      el("div", { class: "form-row" }, field("Note (optionnel)", note),
        el("button", { type: "button", class: "btn btn-primary", onclick: async (ev) => {
          ev.target.disabled = true;
          try { await api.post("/api/admin/restore-points", { note: note.value }); toast("Point de restauration créé.", "success"); reload(); }
          catch (err) { toast(err.message, "error"); ev.target.disabled = false; }
        } }, "Créer un point maintenant")),
      rows.length ? DA.table(["Point", "Pourquoi", ""], rows)
        : el("p", { class: "muted" }, "Aucun point pour l'instant : le premier est créé à la première activité du jour, ou "
          + "avec le bouton ci-dessus."));
  }

  async function spaceDialog(p, reload) {
    let res;
    try { res = await api.get("/api/admin/restore-points/" + p.name + "/spaces"); } catch (err) { toast(err.message, "error"); return; }
    if (!res.spaces.length) { toast("Aucun Space dans ce point.", "error"); return; }
    const select = el("select", { "aria-label": "Space du point" }, res.spaces.map((s) => el("option", { value: s.key },
      s.key + " · " + s.name + (s.exists_now ? " (existe encore)" : " (n'existe plus)"))));
    const key = el("input", { type: "text", maxlength: 10, autocomplete: "off" });
    const name = el("input", { type: "text", maxlength: 100 });
    const fill = () => {
      const s = res.spaces.find((x) => x.key === select.value);
      key.value = s.suggested_key;
      name.value = s.exists_now ? s.name + " (point du " + p.local.slice(0, 10) + ")" : s.name;
    };
    select.addEventListener("change", fill);
    key.addEventListener("input", () => { key.value = key.value.toUpperCase(); });
    fill();
    let close = null;
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        const done = await api.post("/api/admin/restore-points/" + p.name + "/space",
          { key: select.value, new_key: key.value.trim(), new_name: name.value.trim() });
        const skipped = Object.values(done.skipped || {}).reduce((a, n) => a + n, 0);
        close();
        toast("Space " + select.value + " du " + p.local + " récupéré dans " + done.project.key + " ("
          + Object.values(done.counts).reduce((a, n) => a + n, 0) + " lignes"
          + (skipped ? ", " + skipped + " élément(s) unique(s) encore en service non recopié(s)" : "")
          + (done.missing_files ? ", " + done.missing_files + " fichier(s) joint(s) absent(s) : voir sa sauvegarde « avant suppression »" : "")
          + ").", "success");
        reload();
      } catch (err) { toast(err.message, "error"); }
    } },
    el("p", null, "Le Space choisi revient tel qu'il était le " + p.local + ", dans un NOUVEAU Space : rien de ce qui est en service "
      + "n'est écrasé. Copiez ensuite ce qu'il faut dans le Space d'origine, puis archivez la copie."),
    field("Space du point", select), field("Clé du nouveau Space", key, "Libre : 2 à 10 lettres majuscules ou chiffres."),
    field("Nom", name),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Récupérer le Space")));
    close = modal("Récupérer un Space du point du " + p.local, form);
  }

  function revertDialog(p) {
    const ok = el("input", { type: "checkbox" });
    const go = el("button", { type: "button", class: "btn btn-danger", disabled: true }, "Revenir à ce point");
    ok.addEventListener("change", () => { go.disabled = !ok.checked; });
    let close = null;
    go.addEventListener("click", async () => {
      go.disabled = true;
      try {
        const done = await api.post("/api/admin/restore-points/" + p.name + "/revert", { confirm: p.name });
        close();
        toast("Le site est revenu au " + p.local + ". Point « avant retour » gardé ; journal d'audit conservé ("
          + done.audit_rows_kept + " ligne(s)). Reconnectez-vous.", "success");
        setTimeout(() => location.reload(), 2500);
      } catch (err) { toast(err.message, "error"); go.disabled = false; }
    });
    close = modal("Revenir au point du " + p.local, el("div", { class: "form" },
      el("p", null, el("strong", null, "Tout le site revient au " + p.local + " : "), "comptes, droits, Spaces, pages, tickets, "
        + "requirements, tests, heures… Tout ce qui a été saisi depuis est retiré. Le code ne change pas."),
      el("ul", null, el("li", null, "Un point « avant retour » est créé d'abord : vous pouvez revenir à l'état actuel."),
        el("li", null, "Le journal d'audit n'est jamais repris : les lignes écrites depuis le point sont gardées."),
        el("li", null, "Tout le monde est déconnecté : chacun se reconnecte (mot de passe du " + p.local.slice(0, 10) + ")."),
        el("li", null, "Pour une seule erreur dans un Space, préférez « Récupérer un Space… » : rien d'autre ne change.")),
      el("label", { class: "rp-ack" }, ok, " J'ai compris que les saisies faites depuis le " + p.local + " seront retirées."),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"), go)));
  }
})();
