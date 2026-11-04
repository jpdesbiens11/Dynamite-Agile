/* « Membres de mes projets » #/members[/KEY] (core lot v0.10, D-B-027): an
   « Admin du projet » (or a platform administrator) adds, removes and sets
   the right of the members of his project: Lecteur, Éditeur, Admin du
   projet. Nothing else: module settings stay with the administrators. */
(function () {
  "use strict";

  const { api, el, clear, toast, field } = DA;
  const ROLES = [["reader", "Lecteur"], ["editor", "Éditeur"], ["manager", "Admin du Space"]];

  function roleSelect(value, label) {
    return el("select", { "aria-label": label }, ROLES.map(([v, l]) => el("option", { value: v, selected: v === value }, l)));
  }

  async function render(main, parts) {
    let managed;
    try { managed = (await api.get("/api/me/managed-projects")).projects; } catch (err) { toast(err.message, "error"); return; }
    clear(main);
    main.append(el("div", { class: "page-head" }, el("h1", null, DA.t("menu.members")),
      el("p", { class: "muted" }, "Lecteur : lire et commenter. Éditeur : créer et modifier. Admin du Space : éditeur qui gère "
        + "aussi les membres du Space. Chaque changement est journalisé.")));
    if (!managed.length) {
      main.append(el("div", { class: "empty" }, el("p", null, "Vous n'êtes « Admin du Space » d'aucun Space.")));
      return;
    }
    const key = (parts[0] || managed[0].key).toUpperCase();
    const project = managed.find((p) => p.key === key) || managed[0];
    main.append(el("nav", { class: "subtabs" }, managed.map((p) =>
      el("a", { class: p.id === project.id ? "subtab active" : "subtab", href: "#/members/" + p.key }, p.key + " · " + p.name))));
    const body = el("div");
    main.append(body);
    draw(body, project);
  }

  async function draw(body, project) {
    let data;
    try { data = await api.get("/api/projects/" + project.id + "/members"); } catch (err) { toast(err.message, "error"); return; }
    clear(body);
    const put = async (uid, role, who) => {
      try {
        await api.put("/api/projects/" + project.id + "/members/" + uid, { role });
        toast(who + (role ? " : " + ROLES.find(([v]) => v === role)[1] : " retiré du Space") + ".", "success");
      } catch (err) { toast(err.message, "error"); }
      draw(body, project);
    };
    const rows = data.members.map((m) => {
      const sel = roleSelect(m.role, "Droit de " + m.display_name);
      sel.addEventListener("change", () => put(m.id, sel.value, m.display_name));
      return el("tr", null, el("td", null, m.display_name), el("td", { class: "muted" }, m.username), el("td", null, sel),
        el("td", null, el("button", { type: "button", class: "btn btn-small btn-danger", onclick: () => put(m.id, null, m.display_name) }, DA.t("mem.remove"))));
    });
    const who = el("select", { "aria-label": "Personne à ajouter" }, el("option", { value: "" }, "— choisir —"),
      data.candidates.map((u) => el("option", { value: u.id }, u.display_name + " (" + u.username + ")")));
    const role = roleSelect("reader", "Droit");
    body.append(el("div", { class: "panel" }, el("h2", null, DA.t("mem.add")),
      el("div", { class: "form-row" }, field("Personne", who), field(DA.t("mem.role"), role),
        el("button", { type: "button", class: "btn btn-primary", onclick: () => {
          if (!who.value) { toast("Choisissez une personne.", "error"); return; }
          put(who.value, role.value, who.selectedOptions[0].textContent);
        } }, DA.t("mem.add")))),
    DA.table(["Nom", "Identifiant", DA.t("mem.role"), ""], rows));
  }

  DA.coreViews = DA.coreViews || {};
  DA.coreViews.members = render;
})();
