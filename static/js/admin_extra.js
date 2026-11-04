/* Administration - rights matrix, backups / restore, project deletion,
   content protection (core lot v0.10, D-B-027, D-B-029, D-B-030).
   Loaded next to admin.js, which adds these sections to its sub-tabs. */
(function () {
  "use strict";

  const { api, el, clear, toast, modal, field, formatDate } = DA;
  const ROLES = [["", "—"], ["reader", "Lecteur"], ["editor", "Éditeur"], ["manager", "Admin du Space"]];
  const size = (n) => (n > 1048576 ? (n / 1048576).toFixed(1) + " Mo" : Math.max(1, Math.round(n / 1024)) + " Ko");

  /* ---------- Rights matrix: accounts x projects ---------- */
  async function renderRights(body) {
    const data = await api.get("/api/admin/rights");
    clear(body);
    const filter = el("input", { type: "search", placeholder: "Filtrer les comptes…", class: "rights-filter", "aria-label": "Filtrer les comptes" });
    const showArchived = el("input", { type: "checkbox" });
    const holder = el("div", { class: "rights-wrap" });
    body.append(el("p", { class: "muted rights-intro" }, "Un compte × un Space : Lecteur (lire, commenter), Éditeur (créer, modifier), "
      + "Admin du Space (éditeur qui gère aussi les membres de ce Space). Les administrateurs de la plateforme ont tous les droits partout. "
      + "Chaque changement s'applique tout de suite et est journalisé."),
    el("div", { class: "rights-bar" }, filter, el("label", { class: "check" }, showArchived, "Afficher les Spaces archivés")), holder);

    function draw() {
      clear(holder);
      const projects = data.projects.filter((p) => showArchived.checked || !p.is_archived);
      const q = filter.value.trim().toLowerCase();
      const users = data.users.filter((u) => u.is_active && (!q || (u.display_name + " " + u.username).toLowerCase().includes(q)));
      const head = el("tr", null, el("th", { class: "rights-user" }, "Compte"),
        el("th", { class: "rights-proj", title: "Export des pages du wiki en PDF ou Word (D-B-050)" }, "Export PDF / Word"),
        projects.map((p) => el("th", { class: "rights-proj", title: p.name + (p.is_archived ? " (archivé)" : "") }, p.key)));
      const rows = users.map((u) => el("tr", null,
        el("th", { class: "rights-user", scope: "row" }, u.display_name, el("span", { class: "muted rights-login" }, u.username)),
        exportCell(u),
        projects.map((p) => {
          if (u.is_admin) return el("td", { class: "rights-cell rights-admin", title: "Administrateur de la plateforme" }, "Admin");
          const key = u.id + ":" + p.id;
          const sel = el("select", { class: "rights-sel rights-" + (data.cells[key] || "none"), "aria-label": u.display_name + " sur " + p.key },
            ROLES.map(([v, l]) => el("option", { value: v, selected: (data.cells[key] || "") === v }, l)));
          sel.addEventListener("change", async () => {
            try {
              await api.put("/api/admin/rights", { user_id: u.id, project_id: p.id, role: sel.value || null });
              if (sel.value) data.cells[key] = sel.value; else delete data.cells[key];
              sel.className = "rights-sel rights-" + (sel.value || "none");
              toast(u.display_name + " · " + p.key + " : " + (ROLES.find(([v]) => v === sel.value) || ["", "aucun droit"])[1] + ".", "success");
            } catch (err) { toast(err.message, "error"); sel.value = data.cells[key] || ""; }
          });
          return el("td", { class: "rights-cell" }, sel);
        })));
      holder.append(el("table", { class: "data rights-table" }, el("thead", null, head), el("tbody", null, rows)));
    }
    filter.addEventListener("input", draw);
    showArchived.addEventListener("change", draw);
    draw();
  }

  function exportCell(u) {
    if (u.is_admin) return el("td", { class: "rights-cell rights-admin", title: "Les administrateurs exportent toujours" }, "Oui");
    const box = el("input", { type: "checkbox", checked: !!u.can_export, "aria-label": "Export PDF / Word pour " + u.display_name });
    box.addEventListener("change", async () => {
      try {
        await api.put("/api/admin/users/" + u.id + "/prefs", { can_export: box.checked });
        u.can_export = box.checked;
        toast(u.display_name + (box.checked ? " peut exporter les pages en PDF / Word." : " ne peut plus exporter."), "success");
      } catch (err) { toast(err.message, "error"); box.checked = !box.checked; }
    });
    return el("td", { class: "rights-cell" }, box);
  }

  /* ---------- Project actions: backup, delete ---------- */
  function projectActions(project, refresh) {
    return [
      el("a", { class: "btn btn-small", href: "/api/admin/projects/" + project.id + "/backup.zip", download: "",
        title: "Télécharger une sauvegarde complète (une copie reste aussi sur le serveur)" }, "Sauvegarder"),
      project.is_archived ? el("button", { type: "button", class: "btn btn-small btn-danger", onclick: () => deleteDialog(project, refresh) }, "Supprimer…") : null,
    ];
  }

  async function deleteDialog(project, refresh) {
    let impact;
    try { impact = await api.get("/api/admin/projects/" + project.id + "/impact"); } catch (err) { toast(err.message, "error"); return; }
    const confirm = el("input", { type: "text", autocomplete: "off", "aria-label": "Clé du Space" });
    const go = el("button", { type: "submit", class: "btn btn-danger", disabled: true }, "Supprimer définitivement");
    confirm.addEventListener("input", () => { go.disabled = confirm.value.trim().toUpperCase() !== project.key; });
    let close = null;
    const rows = Object.entries(impact.counts).sort((a, b) => b[1] - a[1]).map(([t, n]) => el("tr", null, el("td", null, t), el("td", { class: "num" }, String(n))));
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      go.disabled = true;
      try {
        const res = await api.post("/api/admin/projects/" + project.id + "/delete", { confirm_key: confirm.value });
        close(); toast("Space " + project.key + " supprimé. Sauvegarde conservée : " + res.backup, "success"); refresh();
      } catch (err) { toast(err.message, "error"); go.disabled = false; }
    } },
    el("div", { class: "danger-box" }, el("strong", null, "Action irréversible. "), "Toutes les données du Space " + project.key + " (" + project.name
      + ") seront supprimées : pages, tickets, requirements, changements, plan, références, pièces jointes et heures saisies sur ce Space. "
      + "Une sauvegarde complète est créée automatiquement juste avant (Admin → Update et sauvegardes → Données) et permet de le restaurer."),
    DA.table(["Données", "Lignes"], rows),
    field("Pour confirmer, tapez la clé du Space : " + project.key, confirm),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"), go));
    close = modal("Supprimer le Space " + project.key, form);
  }

  /* ---------- Time sheet: approver and vacation bank of a person (D-B-031) ---------- */
  function userActions(user, users, refresh) {
    return [el("button", { type: "button", class: "btn btn-small", title: "Approbateur et banque de vacances",
      onclick: () => hrDialog(user, users) }, "Feuille de temps…"),
    el("button", { type: "button", class: "btn btn-small", title: "Nouveau compte avec les mêmes droits par Space",
      onclick: () => duplicateDialog(user, refresh) }, "Dupliquer…")];
  }

  /* D-B-045: new account (intern, new colleague) from an existing profile, same project rights. */
  function duplicateDialog(user, refresh) {
    const username = el("input", { type: "text", maxlength: 32, required: true, autocomplete: "off", placeholder: "ex. etudiant.meca" });
    const name = el("input", { type: "text", maxlength: 80, required: true, placeholder: "Prénom Nom" });
    let close = null;
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        const res = await api.post("/api/admin/users/" + user.id + "/duplicate", { username: username.value.trim(), display_name: name.value.trim() });
        close();
        toast(res.user.display_name + " créé avec les droits de " + user.display_name + " sur " + res.projects + " Space(s).", "success");
        if (refresh) refresh();
        DA.admin.showTempPassword(res.user.username, res.temp_password);
      } catch (err) { toast(err.message, "error"); }
    } },
    el("p", { class: "muted" }, "Le nouveau compte reçoit les mêmes droits par Space (Lecteur, Éditeur, Admin du Space), le même "
      + "gestionnaire et les mêmes réglages d'affichage que " + user.display_name + ". Le rôle d'administrateur de la plateforme "
      + "n'est jamais copié. Un mot de passe temporaire est affiché une fois."),
    field("Identifiant", username), field("Nom affiché", name),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer le compte")));
    close = modal("Dupliquer le profil de " + user.display_name, form);
    username.focus();
  }

  async function hrDialog(user, users) {
    let data;
    try { data = await api.get("/api/admin/users/" + user.id + "/prefs"); } catch (err) { toast(err.message, "error"); return; }
    const p = data.prefs;
    const manager = el("select", null, el("option", { value: "" }, "— personne —"),
      users.filter((u) => u.is_active && u.id !== user.id).map((u) => el("option", { value: u.id, selected: u.id === p.manager_id }, u.display_name)));
    const bank = el("input", { type: "number", min: 0, max: 2000, step: 0.5, value: p.vacation_bank_hours == null ? "" : p.vacation_bank_hours });
    const since = el("input", { type: "date", value: p.vacation_bank_date || "" });
    let close = null;
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        await api.put("/api/admin/users/" + user.id + "/prefs", { manager_id: manager.value || null,
          vacation_bank_hours: bank.value === "" ? null : bank.value, vacation_bank_date: since.value || null });
        close(); toast("Feuille de temps de " + user.display_name + " corrigée (journalisé).", "success");
      } catch (err) { toast(err.message, "error"); }
    } },
    el("p", { class: "muted" }, "Normalement saisis par la personne dans ses Paramètres ; l'administrateur corrige au besoin. "
      + "Chaque changement est journalisé et visible par l'approbateur."),
    field("Approbateur (approuve ses feuilles de temps)", manager),
    el("div", { class: "form-row" }, field("Banque de vacances (heures)", bank), field("À la date du", since)),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
    close = modal("Feuille de temps — " + user.display_name, form);
  }

  /* ---------- Backups: list, download, restore, delete ---------- */
  async function renderBackups(body) {
    const data = await api.get("/api/admin/backups");
    clear(body);
    const reload = () => renderBackups(body);
    const file = el("input", { type: "file", accept: ".zip,application/zip" });
    const key = el("input", { type: "text", maxlength: 10, placeholder: "Clé d'origine", autocomplete: "off" });
    key.addEventListener("input", () => { key.value = key.value.toUpperCase(); });
    body.append(el("div", { class: "panel" }, el("h2", null, "Restaurer depuis un fichier"),
      el("p", { class: "muted" }, "La restauration crée toujours un NOUVEAU Space (jamais par-dessus un Space existant). "
        + "Laissez la clé vide pour reprendre celle d'origine, si elle est libre."),
      el("div", { class: "form-row" }, field("Fichier de sauvegarde (.zip)", file), field("Nouvelle clé (optionnel)", key),
        el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
          if (!file.files[0]) { toast("Choisissez le fichier .zip.", "error"); return; }
          try {
            const res = await api.upload("/api/admin/restore?key=" + encodeURIComponent(key.value.trim()), file.files[0]);
            toast("Space " + res.project.key + " restauré.", "success"); reload();
          } catch (err) { toast(err.message, "error"); }
        } }, "Restaurer"))));
    const rows = data.backups.map((b) => el("tr", null,
      el("td", null, el("span", { class: "key" }, (b.project || {}).key || "?"), " ", (b.project || {}).name || ""),
      el("td", null, formatDate(b.created_at)), el("td", null, b.created_by || "—"),
      el("td", null, b.reason === "avant-suppression" ? DA.badge("Avant suppression", "warn") : DA.badge("Manuelle", "neutral")),
      el("td", { class: "num" }, String(b.rows)), el("td", { class: "num" }, size(b.size)),
      el("td", null, el("div", { class: "actions" },
        el("a", { class: "btn btn-small", href: "/api/admin/backups/" + encodeURIComponent(b.name), download: "" }, "Télécharger"),
        el("button", { type: "button", class: "btn btn-small", onclick: () => restoreDialog(b, reload) }, "Restaurer…"),
        el("button", { type: "button", class: "btn btn-small btn-danger", onclick: async () => {
          if (!window.confirm("Supprimer le fichier de sauvegarde " + b.name + " ? Cette copie ne pourra plus être restaurée.")) return;
          try { await api.post("/api/admin/backups/" + encodeURIComponent(b.name) + "/delete", { confirm: b.name }); toast("Sauvegarde supprimée.", "success"); reload(); }
          catch (err) { toast(err.message, "error"); }
        } }, "Supprimer")))));
    body.append(el("h2", null, "Sauvegardes conservées sur le serveur"),
      el("p", { class: "muted" }, "Dossier data/backups/ : à inclure dans la sauvegarde du serveur. Chaque suppression de Space en crée une."),
      DA.table(["Space", "Créée le", "Par", "Type", "Lignes", "Taille", "Actions"], rows));
  }

  function restoreDialog(b, reload) {
    const key = el("input", { type: "text", maxlength: 10, value: (b.project || {}).key || "", autocomplete: "off" });
    key.addEventListener("input", () => { key.value = key.value.toUpperCase(); });
    const name = el("input", { type: "text", maxlength: 100, value: (b.project || {}).name || "" });
    let close = null;
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        const res = await api.post("/api/admin/backups/" + encodeURIComponent(b.name) + "/restore", { key: key.value.trim(), name: name.value.trim() });
        close(); toast("Space " + res.project.key + " restauré (" + Object.values(res.counts).reduce((a, n) => a + n, 0) + " lignes).", "success"); reload();
      } catch (err) { toast(err.message, "error"); }
    } },
    el("p", null, "Restaure « " + b.name + " » dans un nouveau Space. La clé doit être libre."),
    field("Clé du Space restauré", key), field("Nom", name),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Restaurer")));
    close = modal("Restaurer une sauvegarde", form);
  }

  /* ---------- Content protection ---------- */
  async function renderPrivacy(body) {
    const data = await api.get("/api/admin/policy");
    clear(body);
    const items = [
      ["watermark", "Filigrane nominatif", "Nom, identifiant, date-heure et adresse IP en filigrane discret sur toutes les pages : une capture ou une photo d'écran désigne sa source."],
      ["block_print", "Bloquer l'impression", "Ctrl+P et Fichier → Imprimer produisent une page « Impression désactivée » ; chaque tentative est journalisée."],
      ["block_copy", "Bloquer copier / clic droit", "Pas de sélection, de copie ni de menu contextuel sur le contenu (les champs de saisie restent utilisables) ; tentatives journalisées."],
      ["blur_unfocused", "Flouter hors focus", "Le contenu se floute immédiatement quand la fenêtre perd le focus, est masquée, ou quand la touche Windows (Win+Maj+S) ou Impr. écran est enfoncée ; il reste flou jusqu'au clic « Afficher le contenu ». Tentatives journalisées."],
    ];
    body.append(el("div", { class: "danger-box info-box" }, el("strong", null, "Limites à connaître. "),
      "Un site web ne peut pas empêcher une capture faite par le système d'exploitation (Impr. écran, Outil Capture) ni une photo "
      + "de l'écran. Ces mesures dissuadent et tracent (journal d'audit) ; elles ne remplacent pas le contrôle des postes (GPO/MDM) par l'IT."),
    el("div", { class: "privacy-list" }, items.map(([k, label, help]) => {
      const box = el("input", { type: "checkbox", checked: !!data.privacy[k] });
      box.addEventListener("change", async () => {
        try { await api.put("/api/admin/policy", { [k]: box.checked }); toast(label + (box.checked ? " activé" : " désactivé") + " pour tous. Effet au prochain chargement de page.", "success"); }
        catch (err) { toast(err.message, "error"); box.checked = !box.checked; }
      });
      return el("label", { class: "privacy-item" }, box, el("span", null, el("strong", null, label), el("span", { class: "muted" }, help)));
    })));
  }

  /* backups: shown in Update et sauvegardes → Données since D-B-105; config: added by admin_config.js */
  DA.adminExtra = { projectActions, userActions, loaders: Object.assign((DA.adminExtra && DA.adminExtra.loaders) || {},
    { rights: renderRights, backups: renderBackups, privacy: renderPrivacy }) };
})();
