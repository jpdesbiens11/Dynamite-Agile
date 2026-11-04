/* Admin → Update → « Données » and « Site complet » (core lot v0.26, D-B-094).
   Données: sealed export of the accounts (without passwords) and of the chosen Spaces; import step by step (accounts,
   then each Space: skip it or import it as a NEW Space -- a Space in service is never overwritten).
   Site complet: code + exact copy of the database + files, sealed, to move the site; imported only into an empty site.
   The passphrase seals the file (HMAC-SHA256); confidentiality is the job of the medium (encrypted drive, IT). */
(function () {
  "use strict";
  const { api, el, clear, toast, field } = DA;
  const TEXT = {
    data: { api: "/api/data", what: "données", newTag: "0.49.0-data",
      exportHelp: "Comptes (sans mots de passe), Spaces cochés avec tout leur contenu (pages, tickets, Requirements, Gantt, "
        + "essais…) et leurs pièces jointes. Les préférences, objectifs et feuilles de temps hors Space ne voyagent qu'avec « Site complet ».",
      importHelp: "Étapes : contenu du paquet, comptes (les absents sont créés avec un mot de passe temporaire, jamais administrateurs ; "
        + "les existants ne changent pas), puis un Space par étape : un Space qui existe déjà ici n'est jamais écrasé — sautez-le "
        + "ou importez-le sous une autre clé, avec les types cochés." },
    site: { api: "/api/site", what: "site complet", newTag: "0.49.0-site",
      exportHelp: "Le code, une copie exacte de la base (comptes et mots de passe compris, sessions retirées) et les fichiers "
        + "(pièces jointes, captures Audit, archives Q&R). La configuration du serveur et ses certificats ne voyagent pas.",
      importHelp: "Seulement dans un site vide : une nouvelle installation où seul l'admin initial existe. Étapes : sceau, Framework "
        + "(différences de code), chaque Space, comptes et administrateurs. Après « Appliquer », votre session se ferme : "
        + "reconnectez-vous avec un compte du site déménagé." },
  };

  function passphrase(label) {
    return el("input", { type: "password", minlength: 12, autocomplete: "new-password", "aria-label": label, class: "up-pass" });
  }

  function download(url) {
    const a = el("a", { href: url, download: "", hidden: true });
    document.body.append(a);
    a.click();
    a.remove();
  }

  async function exportBox(t, part) {
    const pass = passphrase("Phrase de passe");
    const again = passphrase("Phrase de passe, de nouveau");
    let spaces = null;
    if (part === "data") {
      const projects = (await api.get("/api/admin/projects")).projects;
      spaces = projects.map((p) => el("label", { class: "up-type" }, el("input", { type: "checkbox", value: p.key, checked: true }),
        " " + p.key + " — " + p.name));
    }
    const result = el("div", { "aria-live": "polite" });
    return el("section", { class: "up-step" }, el("h2", null, "1. Exporter — " + t.what),
      el("p", null, t.exportHelp),
      spaces ? el("fieldset", { class: "up-types up-spaces" }, el("legend", null, "Spaces"), spaces) : null,
      field("Phrase de passe (12 caractères au moins)", pass, "Scelle le fichier : sans elle, l'import est refusé ; toute modification aussi. "
        + "Transmettez-la par un autre canal que le fichier."),
      field("Confirmer la phrase de passe", again),
      el("p", { class: "muted" }, "Le fichier contient les données du site : gardez-le sur un support chiffré approuvé par l'IT. "
        + "Il se télécharge une seule fois puis est effacé du serveur."),
      el("button", { type: "button", class: "btn btn-primary", "data-new": t.newTag + "-export", onclick: async (ev) => {
        if (pass.value !== again.value) { toast("Les deux phrases de passe diffèrent. Correctif : retapez-les.", "error"); return; }
        ev.target.disabled = true;
        clear(result);
        result.append(el("p", { class: "muted" }, "Préparation du fichier scellé…"));
        try {
          const body = { passphrase: pass.value };
          if (spaces) body.spaces = spaces.map((l) => l.querySelector("input")).filter((b) => b.checked).map((b) => b.value);
          const out = await api.post(t.api + "/export", body);
          pass.value = again.value = "";
          download(t.api + "/export/" + out.token);
          clear(result);
          result.append(el("p", { class: "up-ok" }, "✓ « " + out.name + " » téléchargé (" + (out.spaces || []).length + " Space(s))."));
        } catch (err) { clear(result); result.append(el("p", { class: "form-error" }, err.message)); }
        ev.target.disabled = false;
      } }, "Exporter (.zip scellé)"), result);
  }

  function importBox(t, part, area) {
    const file = el("input", { type: "file", accept: ".zip,application/zip", hidden: true });
    file.addEventListener("change", async () => {
      const chosen = file.files[0];
      file.value = "";
      if (!chosen) return;
      clear(area);
      area.append(el("p", { class: "muted" }, "Réception de « " + chosen.name + " »…"));
      let token;
      try { token = (await api.upload(t.api + "/upload", chosen)).token; }
      catch (err) { clear(area); area.append(el("p", { class: "form-error" }, err.message)); return; }
      const pass = passphrase("Phrase de passe du paquet");
      clear(area);
      area.append(el("form", { class: "form", onsubmit: async (ev) => {
        ev.preventDefault();
        try {
          const summary = await api.post(t.api + "/open", { token, passphrase: pass.value });
          pass.value = "";
          clear(area);
          area.append(el("p", { class: "up-ok" }, "✓ Sceau vérifié. Revue : " + summary.total + " étape(s)."));
          const review = el("div");
          area.append(review);
          DA.updateReview.show(review, { base: t.api + "/review/" + token, summary,
            applyLabel: part === "site" ? "Appliquer le déménagement" : "Importer les données approuvées",
            confirm: part === "site" ? "Remplacer ce site vide par le site du paquet ? Une sauvegarde est faite, puis le site redémarre."
              : "Importer maintenant ? Rien de ce qui est en service n'est modifié.",
            apply: () => api.post(t.api + "/apply/" + token), onApplied: (done) => applied(area, part, done) });
        } catch (err) { toast(err.message, "error"); }
      } }, el("p", null, "« " + chosen.name + " » reçu. Rien n'est lu avant la vérification du sceau."),
      field("Phrase de passe du paquet", pass), el("div", { class: "form-actions" },
        el("button", { type: "submit", class: "btn btn-primary" }, "Vérifier le sceau et ouvrir la revue"))));
      pass.focus();
    });
    return el("section", { class: "up-step" }, el("h2", null, "2. Importer — " + t.what), el("p", null, t.importHelp),
      el("button", { type: "button", class: "btn btn-primary", "data-new": t.newTag + "-import", onclick: () => file.click() },
        "Importer un paquet scellé…"), file);
  }

  function applied(area, part, done) {
    clear(area);
    if (part === "site") {
      area.append(el("p", { class: "up-ok" }, "✓ Site déménagé (version " + done.version + "). Sauvegarde de l'état précédent : "
        + done.backup + ". Reconnectez-vous avec un compte du site déménagé."));
      toast("Site déménagé. Reconnexion…", "success");
      setTimeout(() => location.reload(), done.restarting ? 8000 : 2500);
      return;
    }
    area.append(el("div", null, el("p", { class: "up-ok" }, "✓ Import terminé : " + done.spaces.length + " Space(s) créé(s)."),
      done.spaces.length ? DA.table(["Space du paquet", "Nouveau Space", "Liens vidés"], done.spaces.map((s) => el("tr", null,
        el("td", null, s.from), el("td", null, el("a", { href: "#/dynamite" }, s.key)), el("td", null, String(s.lost_links), s.lost_links ? el("span", { class: "muted" }, " — "
          + Object.entries(s.lost_detail || {}).map(([k, n]) => k + " : " + n).join(", ")) : null)))) : null,
      done.created.length ? el("div", { class: "info-box" }, el("strong", null, "Comptes créés — mots de passe temporaires, affichés une seule fois :"),
        DA.table(["Identifiant", "Mot de passe temporaire"], done.created.map((c) => el("tr", null, el("td", null, c.username),
          el("td", null, el("code", null, c.temp_password)))))) : null));
    toast("Données importées.", "success");
  }

  DA.adminUpdateData = {
    async render(box, part) {
      const t = TEXT[part];
      const grid = el("div", { class: "up-steps" });
      const area = el("div", { class: "up-report", "aria-live": "polite" });  // the review takes the full width
      box.append(grid, area);
      try { grid.append(await exportBox(t, part), importBox(t, part, area)); }
      catch (err) { box.append(el("p", { class: "form-error" }, err.message)); }
    },
  };
})();
