/* Dynamite | Agile - administration screens: users, projects, audit log. */
(function () {
  "use strict";

  const { api, el, clear, field, badge, table, toast, modal, formatDate } = DA;

  /* Core lot v0.18 (D-A-039): the Admin tab (far right, administrators only), sections grouped by what they manage. */
  /* D-B-105: Configuration and Sauvegardes joined Update in one tab « Update et sauvegardes » (five parts) */
  const GROUPS = [["Comptes", [["users", "Utilisateurs"], ["rights", "Droits"], ["rules", "Règles d'accès"], ["guest", "Accès invité"]]],
    ["Spaces", [["start", "Commencer"], ["projects", "Spaces"], ["setup", "Setup des Spaces"]]],
    ["Plateforme", [["update", "Update et sauvegardes"], ["revisions", "Révisions"], ["transport", "Sécurité réseau"],
      ["privacy", "Confidentialité"], ["audit", "Journal d'audit"], ["bob", "Bob (agent IA)"], ["mail", "Courriel"]]]];
  const NEW = { start: "0.60.07-starter", update: "0.50.1-admin-maintenance", transport: "0.46.0-admin-transport", revisions: "0.50.11-admin-revisions", bob: "0.60.36-bob", guest: "0.60.63-guest", mail: "0.60.73-mail" };  // D-A-049 badges
  const MOVED = { config: "config", backups: "data" };  // old addresses -> part of « Update et sauvegardes »
  const SECTIONS = GROUPS.flatMap(([, items]) => items);

  const ACTION_LABELS = {
    initial_admin_created: "Compte admin initial créé",
    login: "Connexion",
    login_failed: "Échec de connexion",
    guest_login: "Visite invité",
    guest_access_changed: "Accès invité modifié",
    logout: "Déconnexion",
    password_changed: "Mot de passe changé",
    password_reset: "Mot de passe réinitialisé",
    cli_reset_password: "Mot de passe réinitialisé (console serveur)",
    user_created: "Utilisateur créé",
    user_updated: "Utilisateur modifié",
    project_created: "Space créé",
    project_updated: "Space modifié",
    member_set: "Membre ajouté ou rôle changé",
    member_removed: "Membre retiré",
  };

  function render(container, section, sub) {
    if (MOVED[section]) { location.replace("#/admin/update/" + MOVED[section]); return; }  // no history trap
    if (!SECTIONS.some(([id]) => id === section)) section = "users";
    const body = el("div");
    container.append(
      el("div", { class: "page-head" }, el("h1", null, "Administration")),
      el("nav", { class: "subtabs admin-subtabs", "aria-label": "Sections d'administration" },
        GROUPS.flatMap(([group, items], i) => [i ? el("span", { class: "tab-sep", "aria-hidden": "true" }) : null,
          el("span", { class: "subtab-group" }, group)].concat(items.map(([id, label]) => el("a", { href: "#/admin/" + id,
          class: id === section ? "subtab active" : "subtab", "aria-current": id === section ? "page" : null,
          "data-new": NEW[id] || null }, label))))
          .filter(Boolean)),
      body);
    const loaders = Object.assign({ users: renderUsers, projects: renderProjects, audit: renderAudit, setup: renderSetup,
      rules: (b) => DA.adminRules.render(b), start: (b) => DA.adminStarter.render(b), bob: (b) => DA.adminBob.render(b),
      transport: (b) => DA.adminTransport.render(b), revisions: (b) => DA.baselines.render(b) }, (DA.adminExtra && DA.adminExtra.loaders) || {},
    { update: (b, sub) => DA.adminUpdate.render(b, sub) });
    loaders[section](body, sub).catch((err) => {
      clear(body);
      body.append(el("p", { class: "form-error" }, err.message));
    });
  }

  /* D-A-039: every set-up screen of the platform and of each Space, in one place (administrators only). */
  async function renderSetup(body) {
    const data = await api.get("/api/admin/projects");
    const mods = new Set(DA.session.modules.filter((m) => m.available).map((m) => m.key));
    const link = (label, href) => el("a", { class: "btn btn-small", href }, label);
    body.append(el("p", { class: "muted" }, "Les écrans de configuration, réservés aux administrateurs. Ils n'apparaissent "
      + "plus dans les menus des autres comptes : chaque module les regroupe sous « ⚙ Admin » dans sa marge gauche."),
    el("h2", null, "Réglages de la plateforme"),
    table(["Module", "Réglage", ""], [
      mods.has("testing") ? ["Testing", "Listes centrales : Test Equipment, Test Locations, Product Functions, Acronyms, Definitions",
        link("Ouvrir", "#/testing/lists")] : null,
      mods.has("timesheet") ? ["Timesheet", "Spaces et organismes, Funding Spaces et Budget Lines", link("Ouvrir", "#/timesheet/projets")] : null,
      mods.has("timesheet") ? ["Timesheet", "Export Excel des heures", link("Ouvrir", "#/timesheet/export")] : null,
      ["Plateforme", "Configuration .md versionnée", link("Ouvrir", "#/admin/update/config")],
    ].filter(Boolean).map((r) => el("tr", null, r.map((c) => el("td", null, c))))),
    el("h2", null, "Réglages par Space"),
    table(["Space", "Nom", "Réglages"], data.projects.filter((p) => !p.is_archived).map((p) => el("tr", null,
      el("td", null, el("strong", null, p.key)), el("td", null, p.name),
      el("td", { class: "admin-setup-links" }, [
        mods.has("agile") ? link("Agile : Paramètres du Space", "#/agile/" + p.key + "/settings") : null,
        mods.has("dynamite") ? link("Wiki Dynamite", "#/dynamite/" + p.key) : null,
        link("Membres et droits", "#/admin/rights"), link("Sauvegarde", "#/admin/update/data")])))));
  }

  function roleSelect(value) {
    const select = el("select", { "aria-label": "Rôle" },
      el("option", { value: "reader" }, "Lecteur"),
      el("option", { value: "editor" }, "Éditeur"),
      el("option", { value: "manager" }, "Admin du Space"));
    select.value = value;
    return select;
  }

  async function run(action, successMessage, refresh) {
    try {
      const result = await action();
      if (successMessage) toast(successMessage, "success");
      if (refresh) await refresh();
      return result;
    } catch (err) {
      toast(err.message, "error");
      return null;
    }
  }

  /* ---------------- Users ---------------- */
  function showTempPassword(username, password) {
    const copy = el("button", {
      type: "button", class: "btn",
      onclick: async () => {
        try {
          await navigator.clipboard.writeText(password);
          toast("Mot de passe copié.", "success");
        } catch (err) {
          toast("Copie automatique indisponible : sélectionnez le texte.", "error");
        }
      },
    }, "Copier");
    modal("Mot de passe temporaire", el("div", null,
      el("p", null, "Mot de passe temporaire de ", el("strong", null, username), " :"),
      el("p", { class: "temp-password" }, password),
      el("p", { class: "muted" }, "Transmettez-le de vive voix ou par un canal sûr. Il ne sera plus affiché, " +
        "et l'utilisateur devra le remplacer à sa première connexion."),
      el("div", { class: "form-actions" }, copy)));
  }

  /* 0.60.01: « Profil d'études » of an account (génie mécanique, design industriel…), for a multidisciplinary team */
  const PROFILES = ["Génie mécanique", "Génie électrique", "Génie informatique", "Génie robotique", "Génie industriel",
    "Design industriel", "Génie chimique", "Génie biotechnologique"];
  function profileUser(user, refresh) {
    const input = el("input", { type: "text", maxlength: 80, value: user.study_profile || "", list: "da-study-profiles",
      placeholder: "ex. Génie mécanique" });
    const options = el("datalist", { id: "da-study-profiles" }, PROFILES.map((p) => el("option", { value: p })));
    let close = null;
    const form = el("form", {
      onsubmit: async (ev) => {
        ev.preventDefault();
        const ok = await run(() => api.patch("/api/admin/users/" + user.id, { study_profile: input.value.trim() }),
          "Profil d'études mis à jour.", refresh);
        if (ok) close();
      },
    }, field("Profil d'études", input, "Le programme de la personne : il aide à former une équipe multidisciplinaire."), options,
      el("div", { class: "form-actions" }, el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
    close = modal("Profil d'études — " + user.display_name, form);
  }

  function renameUser(user, refresh) {
    const input = el("input", { type: "text", maxlength: 80, value: user.display_name, required: true });
    let close = null;
    const form = el("form", {
      onsubmit: async (ev) => {
        ev.preventDefault();
        const ok = await run(() => api.patch("/api/admin/users/" + user.id, { display_name: input.value.trim() }),
          "Nom mis à jour.", refresh);
        if (ok) close();
      },
    }, field("Nom affiché", input),
      el("div", { class: "form-actions" }, el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
    close = modal("Renommer " + user.username, form);
  }

  async function renderUsers(body) {
    const data = await api.get("/api/admin/users");
    clear(body);
    const refresh = () => renderUsers(body);
    const me = DA.session.user.id;

    const username = el("input", { type: "text", maxlength: 32, required: true, autocomplete: "off", placeholder: "prenom.nom" });
    const displayName = el("input", { type: "text", maxlength: 80, required: true, autocomplete: "off" });
    const isAdmin = el("input", { type: "checkbox" });
    const email = el("input", { type: "text", inputmode: "email", spellcheck: "false", maxlength: 254, autocomplete: "off", placeholder: "prenom@exemple.ca", "data-new": "0.60.73-user-email" });
    const profile = el("input", { type: "text", maxlength: 80, autocomplete: "off", list: "da-study-profiles-new",
      placeholder: "ex. Génie mécanique", "data-new": "0.60.01-study-profile" });
    const form = el("form", {
      class: "panel",
      onsubmit: async (ev) => {
        ev.preventDefault();
        const result = await run(() => api.post("/api/admin/users", {
          username: username.value.trim(), display_name: displayName.value.trim(), is_admin: isAdmin.checked,
          study_profile: profile.value.trim(), email: email.value.trim(),
        }), null, refresh);
        if (result) showTempPassword(result.user.username, result.temp_password);
      },
    },
      el("h2", null, "Ajouter un utilisateur"),
      el("div", { class: "form-row" },
        field("Identifiant", username),
        field("Nom affiché", displayName),
        field("Profil d'études", profile),
        field("Courriel", email),
        el("datalist", { id: "da-study-profiles-new" }, PROFILES.map((p) => el("option", { value: p }))),
        el("label", { class: "check" }, isAdmin, "Administrateur"),
        el("button", { type: "submit", class: "btn btn-primary" }, "Ajouter l'utilisateur")));

    const rows = data.users.map((user) => {
      const self = user.id === me;
      const selfTitle = self ? "Action impossible sur votre propre compte" : null;
      let status = badge("Actif", "ok");
      if (!user.is_active) status = badge("Désactivé", "off");
      else if (user.must_change_password) status = badge("Mot de passe temporaire", "warn");

      return el("tr", { class: user.is_active ? null : "row-inactive" },
        el("td", { class: "code" }, user.username),
        el("td", null, user.display_name, user.email ? el("div", { class: "muted small", "data-new": "0.60.73-user-email" }, user.email) : null),
        el("td", null, user.study_profile || el("span", { class: "muted" }, "—")),
        el("td", null, user.is_admin ? badge("Admin", "admin") : badge("Membre", "reader")),
        el("td", null, status),
        el("td", null, el("div", { class: "actions" },
          el("button", { type: "button", class: "btn btn-small", onclick: () => renameUser(user, refresh) }, "Renommer"),
          el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.01-study-profile-edit",
            onclick: () => profileUser(user, refresh) }, "Profil…"),
          DA.adminMail ? DA.adminMail.emailButton(user, refresh) : null,  // 0.60.73 (D-O-079)
          DA.adminExtra ? DA.adminExtra.userActions(user, data.users, refresh) : null,
          el("button", {
            type: "button", class: "btn btn-small", disabled: self, title: selfTitle,
            onclick: () => run(() => api.patch("/api/admin/users/" + user.id, { is_admin: !user.is_admin }),
              "Droits mis à jour.", refresh),
          }, user.is_admin ? "Retirer admin" : "Rendre admin"),
          el("button", {
            type: "button", class: "btn btn-small", disabled: self, title: selfTitle,
            onclick: async () => {
              const text = await run(() => api.post("/api/admin/users/" + user.id + "/reset-password"), null, refresh);
              if (text) showTempPassword(user.username, text.temp_password);
            },
          }, "Nouveau mot de passe"),
          el("button", {
            type: "button", class: user.is_active ? "btn btn-small btn-danger" : "btn btn-small",
            disabled: self, title: selfTitle,
            onclick: () => {
              if (user.is_active && !confirm("Désactiver " + user.username + " ? Ses sessions seront fermées.")) return;
              run(() => api.patch("/api/admin/users/" + user.id, { is_active: !user.is_active }),
                user.is_active ? "Utilisateur désactivé." : "Utilisateur réactivé.", refresh);
            },
          }, user.is_active ? "Désactiver" : "Réactiver"))));
    });

    body.append(form, table(["Identifiant", "Nom", "Profil d'études", "Rôle", "Status", "Actions"], rows));
  }

  /* ---------------- Projects ---------------- */
  function editProject(project, refresh) {
    const name = el("input", { type: "text", maxlength: 100, value: project.name, required: true });
    const description = el("textarea", { maxlength: 500, rows: 3 });
    description.value = project.description || "";
    let close = null;
    const form = el("form", {
      onsubmit: async (ev) => {
        ev.preventDefault();
        const ok = await run(() => api.patch("/api/admin/projects/" + project.id,
          { name: name.value.trim(), description: description.value.trim() }), "Space mis à jour.", refresh);
        if (ok) close();
      },
    }, field("Nom", name), field("Description", description),
      el("div", { class: "form-actions" }, el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
    close = modal("Modifier " + project.key, form);
  }

  async function renderProjects(body, selectedId) {
    if (/^\d+$/.test(String(selectedId || "")) && DA.spaceCard) { await DA.spaceCard.render(body, Number(selectedId)); return; }  // D-B-133
    const data = await api.get("/api/admin/projects");
    const demo = await api.get("/api/admin/demo").catch(() => null);  // 0.60.49 (D-O-058)
    clear(body);
    const refresh = () => renderProjects(body, selectedId);

    const key = el("input", { type: "text", maxlength: 10, required: true, autocomplete: "off", placeholder: "EQP" });
    key.addEventListener("input", () => { key.value = key.value.toUpperCase(); });
    const name = el("input", { type: "text", maxlength: 100, required: true, autocomplete: "off" });
    const description = el("input", { type: "text", maxlength: 500, autocomplete: "off" });
    const form = el("form", {
      class: "panel",
      onsubmit: async (ev) => {
        ev.preventDefault();
        const result = await run(() => api.post("/api/admin/projects", {
          key: key.value.trim(), name: name.value.trim(), description: description.value.trim(),
        }), "Space créé.");
        if (result) renderProjects(body, result.project.id);
      },
    },
      el("h2", null, "Créer un Space"),
      el("div", { class: "form-row" },
        field("Clé (préfixe des tickets)", key),
        field("Nom", name),
        field("Description", description),
        el("button", { type: "submit", class: "btn btn-primary" }, "Créer le Space")));

    const rows = data.projects.map((project) => el("tr", { class: project.is_archived ? "row-inactive" : null },
      el("td", null, el("span", { class: "key" }, project.key)),
      el("td", null, project.name),
      el("td", null, String(project.member_count)),
      el("td", null, project.is_archived ? badge("Archivé", "off") : badge("Actif", "ok")),
      el("td", null, el("div", { class: "actions" },
        el("a", { class: "btn btn-small btn-primary", href: "#/admin/projects/" + project.id, "data-new": "0.50.14-space-card" }, "Fiche"),
        el("button", { type: "button", class: "btn btn-small", onclick: () => renderProjects(body, project.id) }, "Gérer les membres"),
        el("button", { type: "button", class: "btn btn-small", onclick: () => editProject(project, refresh) }, "Modifier"),
        el("button", {
          type: "button", class: "btn btn-small",
          onclick: () => run(() => api.patch("/api/admin/projects/" + project.id, { is_archived: !project.is_archived }),
            project.is_archived ? "Space réactivé." : "Space archivé.", refresh),
        }, project.is_archived ? "Désarchiver" : "Archiver"),
        demo && project.key === demo.key ? el("button", {  // 0.60.49 (D-O-058): hidden for everyone, pages still reachable by link
          type: "button", class: "btn btn-small", "data-new": "0.60.49-demo-hide",
          "data-tip": "DEMO disparaît de toutes les listes ; la documentation de Help reste accessible.",
          onclick: () => run(() => api.put("/api/admin/demo", { hidden: !demo.hidden }),
            demo.hidden ? "DEMO est de nouveau visible pour tous." : "DEMO est caché pour tous.", refresh),
        }, demo.hidden ? "Montrer à tous" : "Cacher pour tous") : null,
        DA.adminExtra ? DA.adminExtra.projectActions(project, refresh) : null))));

    body.append(form, el("div", { class: "sc-entry" }, DA.spaceCopy ? DA.spaceCopy.button((made) => renderProjects(body, made.project.id)) : null),
      table(["Clé", "Nom", "Membres", "Status", "Actions"], rows));  // D-B-099

    const selected = data.projects.find((p) => p.id === selectedId);
    if (selected) body.append(await membersPanel(selected, refresh));
  }

  async function membersPanel(project, refresh) {
    const [memberData, userData] = await Promise.all([
      api.get("/api/admin/projects/" + project.id + "/members"),
      api.get("/api/admin/users"),
    ]);
    const memberIds = new Set(memberData.members.map((m) => m.id));
    const candidates = userData.users.filter((u) => u.is_active && !u.is_admin && !memberIds.has(u.id));
    const base = "/api/admin/projects/" + project.id + "/members/";

    const userPicker = el("select", null, candidates.length
      ? candidates.map((u) => el("option", { value: u.id }, u.display_name + " (" + u.username + ")"))
      : el("option", { value: "" }, "Tous les utilisateurs sont déjà membres"));
    const newRole = roleSelect("reader");
    const addForm = el("form", {
      class: "form-row",
      onsubmit: (ev) => {
        ev.preventDefault();
        if (!userPicker.value) return;
        run(() => api.put(base + userPicker.value, { role: newRole.value }), "Membre ajouté.", refresh);
      },
    }, field("Utilisateur", userPicker), field("Rôle", newRole),
      el("button", { type: "submit", class: "btn btn-primary", disabled: !candidates.length }, "Ajouter au Space"));

    const rows = memberData.members.map((member) => {
      const select = roleSelect(member.role);
      select.addEventListener("change", async () => {
        const ok = await run(() => api.put(base + member.id, { role: select.value }), "Rôle mis à jour.");
        if (!ok) select.value = member.role;
      });
      return el("tr", { class: member.is_active ? null : "row-inactive" },
        el("td", { class: "code" }, member.username),
        el("td", null, member.display_name),
        el("td", null, select),
        el("td", null, el("button", {
          type: "button", class: "btn btn-small btn-danger",
          onclick: () => {
            if (!confirm("Retirer " + member.username + " du Space " + project.key + " ?")) return;
            run(() => api.del(base + member.id), "Membre retiré.", refresh);
          },
        }, "Retirer")));
    });

    return el("section", { class: "panel members" },
      el("h2", null, "Membres de " + project.key + " : " + project.name),
      el("p", { class: "muted" }, "Les administrateurs voient tous les Spaces et n'ont pas besoin d'y être ajoutés."),
      addForm,
      table(["Identifiant", "Nom", "Rôle", ""], rows));
  }

  DA.adminMembersPanel = membersPanel;  // the Space card shows it too (D-B-133)

  /* ---------------- Audit ---------------- */
  async function renderAudit(body) {
    const data = await api.get("/api/admin/audit?limit=200");
    clear(body);
    const rows = data.entries.map((entry) => el("tr", null,
      el("td", { class: "nowrap" }, formatDate(entry.ts)),
      el("td", { class: "code" }, entry.username || "système"),
      el("td", null, ACTION_LABELS[entry.action] || entry.action),
      el("td", { class: "code" }, entry.object_type + (entry.object_id ? " #" + entry.object_id : "")),
      el("td", { class: "muted code" }, entry.details ? JSON.stringify(entry.details) : ""),
      el("td", { class: "muted code" }, entry.ip || "")));
    body.append(
      el("p", { class: "muted" }, "Les 200 dernières actions, de la plus récente à la plus ancienne."),
      table(["Date", "Utilisateur", "Action", "Objet", "Détails", "Adresse IP"], rows));
  }

  DA.admin = { render, showTempPassword };
})();
