/* Admin → Spaces → « Fiche » of ONE Space (core lot v0.34, D-B-133): #/admin/projects/<id>.
   Renommer (name, description; the key never changes), Dupliquer (everything, next free key), Enregistrer sous… (key,
   name, the tabs to take), Sauvegarder (.zip), Archiver / Désarchiver, Supprimer (archived only, backup first),
   members, and what the Space holds tab by tab. Copies reuse « Copier / composer un Space » (D-B-099): always a new Space, nothing existing is touched. */
(function () {
  "use strict";

  const { api, el, clear, field, badge, table, toast, modal } = DA;

  function rename(card, reload) {
    const p = card.project;
    const name = el("input", { type: "text", maxlength: 100, value: p.name, required: true });
    const description = el("textarea", { maxlength: 500, rows: 3 });
    description.value = p.description || "";
    let close = null;
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        await api.patch("/api/admin/projects/" + p.id, { name: name.value.trim(), description: description.value.trim() });
        close(); toast("Space renommé.", "success"); reload();
      } catch (err) { toast(err.message, "error"); }
    } },
    el("p", { class: "muted" }, "La clé " + p.key + " ne change pas : les références déjà émises (" + p.key + "-12, REQ-" + p.key
      + "-…) restent justes. Pour une autre clé : « Enregistrer sous… »."),
    field("Nom", name), field("Description", description),
    el("div", { class: "form-actions" }, el("button", { type: "submit", class: "btn btn-primary" }, "Renommer")));
    close = modal("Renommer " + p.key, form);
  }

  async function copy(card, body, done) {
    try {
      const made = await api.post("/api/admin/projects/" + card.project.id + "/copy", body);
      toast("Space " + made.project.key + " créé" + (made.lost_links ? " (" + made.lost_links + " lien(s) vers du contenu non copié vidé(s))" : "") + ".", "success");
      done(made);
    } catch (err) { toast(err.message, "error"); }
  }

  function saveAs(card, done) {
    const p = card.project;
    const key = el("input", { type: "text", maxlength: 10, required: true, value: card.suggested_key, autocomplete: "off" });
    key.addEventListener("input", () => { key.value = key.value.toUpperCase(); });
    const name = el("input", { type: "text", maxlength: 100, required: true, value: p.name + " (copie)" });
    const description = el("input", { type: "text", maxlength: 500, value: p.description || "" });
    const boxes = card.parts.map(({ part, label }) => {
      const box = el("input", { type: "checkbox", checked: true, value: part });
      return { box, row: el("label", { class: "sc-check" }, box, " " + label) };
    });
    let close = null;
    const form = el("form", { class: "form sc-form", onsubmit: async (ev) => {
      ev.preventDefault();
      close();
      await copy(card, { key: key.value.trim(), name: name.value.trim(), description: description.value.trim(),
        parts: boxes.filter((b) => b.box.checked).map((b) => b.box.value) }, done);
    } },
    el("p", { class: "muted" }, "Crée un NOUVEAU Space à partir de " + p.key + ". Un onglet décoché part vide, comme dans un Space neuf "
      + "(sa structure est prête). Les liens vers du contenu non copié sont vidés."),
    el("div", { class: "form-row" }, field("Clé du nouveau Space", key), field("Nom", name), field("Description", description)),
    el("div", { class: "sc-grid" }, boxes.map((b) => b.row)),
    el("div", { class: "form-actions" }, el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer sous")));
    close = modal("Enregistrer " + p.key + " sous…", form);
  }

  async function render(body, id) {
    clear(body);
    const card = await api.get("/api/admin/projects/" + id + "/card");
    const p = card.project;
    const reload = () => render(body, id);
    const goto = (made) => { location.hash = "#/admin/projects/" + made.project.id; };
    const actions = el("div", { class: "actions spc-actions" },
      el("button", { type: "button", class: "btn", onclick: () => rename(card, reload) }, "Renommer…"),
      el("button", { type: "button", class: "btn", "data-tip": "Copie complète, clé " + card.suggested_key,
        onclick: () => copy(card, {}, goto) }, "Dupliquer"),
      el("button", { type: "button", class: "btn", onclick: () => saveAs(card, goto) }, "Enregistrer sous…"),
      p.key === "HEADLAMP" ? null : el("a", { class: "btn", href: "/api/starter/export?space=" + encodeURIComponent(p.key) + "&download=1",
        download: "", "data-new": "0.60.43-export-starter", "data-tip": "Ce Space comme fichier Project Starter : le modèle qu'un assistant IA "
          + "suit pour préparer le prochain produit (⚙ Admin → Spaces → Commencer → Modèle)" }, "Exporter comme modèle (IA)"),
      el("a", { class: "btn", href: "/api/admin/projects/" + p.id + "/backup.zip", download: "",
        "data-tip": "Sauvegarde complète du Space (une copie reste sur le serveur) ; se restaure dans Update et sauvegardes" }, "Sauvegarder (.zip)"),
      el("button", { type: "button", class: "btn", onclick: async () => {
        try {
          await api.patch("/api/admin/projects/" + p.id, { is_archived: !p.is_archived });
          toast(p.is_archived ? "Space réactivé." : "Space archivé.", "success"); reload();
        } catch (err) { toast(err.message, "error"); }
      } }, p.is_archived ? "Désarchiver" : "Archiver"),
      p.is_archived && DA.adminExtra ? DA.adminExtra.projectActions(p, () => { location.hash = "#/admin/projects"; })[1] : null,
      p.is_archived ? null : el("button", { type: "button", class: "btn", "data-tip": "Chaque onglet s'ouvre directement sur ce Space (votre réglage)",
        onclick: async () => {
          try {
            const mine = DA.spaces.defaultKey() === p.key;
            const res = await api.put("/api/me/prefs", { default_space: mine ? "" : p.key });
            DA.session.prefs = res.prefs || DA.session.prefs;
            toast(mine ? "Plus de Space par défaut." : p.key + " devient votre Space par défaut.", "success"); reload();
          } catch (err) { toast(err.message, "error"); }
        } }, DA.spaces.defaultKey() === p.key ? "★ Mon Space par défaut" : "☆ Définir comme mon Space par défaut"));
    body.append(
      el("p", null, el("a", { href: "#/admin/projects" }, "← Tous les Spaces")),
      el("div", { class: "page-head spc-head", "data-new": "0.50.14-space-card" },
        el("h2", null, el("span", { class: "key" }, p.key), " " + p.name, " ", p.is_archived ? badge("Archivé", "off") : badge("Actif", "ok")),
        p.description ? el("p", { class: "muted" }, p.description) : null,
        el("p", { class: "muted" }, "Créé le " + (p.created_at || "").slice(0, 10) + " · Space par défaut de " + card.default_for
          + " compte(s).")),
      actions);
    if (p.is_archived) {
      body.append(el("p", { class: "muted" }, "Archivé : invisible dans les listes et les onglets, données gardées. « Supprimer… » "
        + "n'est offert qu'à un Space archivé, avec une sauvegarde juste avant."));
    }
    body.append(el("h3", null, "Contenu par onglet"),
      table(["Onglet", "Contenu"], card.content.map((c) => el("tr", null, el("td", null, c.tab),
        el("td", null, c.count ? c.count + " " + c.unit : el("span", { class: "muted" }, "vide — structure prête"))))));
    const members = el("div");
    body.append(members);
    if (DA.adminMembersPanel) members.append(await DA.adminMembersPanel(p, reload));
  }

  DA.spaceCard = { render };
})();
